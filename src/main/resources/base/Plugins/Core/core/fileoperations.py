from core.transfer_workers import DONE, TransferWorkers, WorkerProgress
from core.util import is_parent
from fman import Task, YES, NO, YES_TO_ALL, NO_TO_ALL, ABORT, OK
from fman.url import basename, join, dirname, splitscheme, relpath, \
	as_human_readable
from os.path import pardir
from queue import Queue
from threading import Lock, Thread
from core.move_rollback import MoveRollback

import fman.fs

def _describe_error(error):
	# Providers may wrap the OS error, e.g. FileExistsError(path) from WinError 183.
	for candidate in (error, error.__cause__):
		strerror = getattr(candidate, 'strerror', None)
		if strerror:
			return strerror[0].lower() + strerror[1:]
	return error.__class__.__name__

class FileTreeOperation(Task):
	def __init__(
		self, descr_verb, files, dest_dir, dest_name=None, fs=fman.fs
	):
		if dest_name and len(files) > 1:
			raise ValueError(
				'Destination name can only be given when there is one file.'
			)
		super().__init__(self._get_title(descr_verb, files))
		self._files = files
		self._dest_dir = dest_dir
		self._descr_verb = descr_verb
		self._dest_name = dest_name
		self._fs = fs
		self._src_dir = dirname(files[0])
		self._queue = Queue()
		self._gather_aborted = False
		self._gather_canceled = False
		self._ended_early = False
		self._gather_exception = None
		self._stop_gathering = False
		# Overwrite prompts come from the gathering thread, error prompts from
		# the transferring one. A second modal would open inside the first.
		self._alert_lock = Lock()
		# Workers add to the total size and progress at the same time. Never
		# held by the GUI thread, so set_size(...) may wait for it.
		self._progress_lock = Lock()
		self._worker_count = 1
		self._cannot_move_to_self_shown = False
		self._override_all = None
		self._ignore_exceptions = False
	def _transfer(self, src, dest):
		raise NotImplementedError()
	def _prepare_transfer(self, src, dest):
		raise NotImplementedError()
	def _can_transfer_samefile(self):
		raise NotImplementedError()
	def _does_postprocess_directory(self):
		return False
	def _postprocess_directory(self, src_dir_path):
		return None
	def _get_worker_count(self):
		return self._fs.get_parallel_transfers(
			self._files[0], self._get_dest_dir_url()
		)
	def __call__(self):
		# Gathering walks the whole tree first, which on a remote file system
		# takes long. So it runs on its own thread while the workers already
		# transfer the files found so far.
		self.set_text('Gathering files...')
		gatherer = Thread(target=self._gather_in_background, daemon=True)
		gatherer.start()
		try:
			self._run_gathered_tasks()
		finally:
			self._stop_gathering = True
			gatherer.join()
		if self._gather_exception is not None:
			raise self._gather_exception
	def _gather_in_background(self):
		try:
			self._gather_aborted = not self._gather_files()
		except Task.Canceled:
			self._gather_canceled = True
		except Exception as e:
			self._gather_exception = e
		finally:
			self._queue.put(DONE)
	def _run_gathered_tasks(self):
		self._worker_count = self._get_worker_count()
		workers = TransferWorkers(
			self._worker_count, self._queue, self._run_one,
			should_stop=lambda: self._gather_aborted
		)
		if self._worker_count > 1:
			# The worker rows show the files, so this keeps the overall title.
			self.set_text(self.get_title())
			self.show_workers(workers)
		workers.start()
		workers.join()
	def _run_one(self, worker, task, is_last):
		# When the transfers end early, the walk must stop too: the other
		# workers wait for its end of the queue.
		try:
			keep_going = self._transfer_one(worker, task, is_last)
		except BaseException:
			self._stop_gathering = True
			raise
		if not keep_going:
			self._stop_gathering = True
		return keep_going
	def _transfer_one(self, worker, task, is_last):
		self.check_canceled()
		size = task.get_size()
		if size:
			with self._progress_lock:
				# The total grows as tasks start: it is unknown while gathering.
				self.set_size(self.get_size() + size)
		progress = WorkerProgress(
			self._dialog, self._progress_lock, worker, task,
			forward_text=self._worker_count == 1
		)
		try:
			self._run_with_dialog(task, progress)
		except (OSError, IOError) as e:
			title = task.get_title()
			message = 'Error ' + (title[0].lower() + title[1:])
			if not self._handle_exception(message, is_last, e):
				return False
			progress.set_progress(size)
		else:
			self._on_task_done(task)
		finally:
			worker.title = ''
		return True
	def _on_task_done(self, task):
		pass
	def _gather_files(self):
		# Checked before the destination is created: a rejected transfer must
		# not leave a new folder behind, least of all inside its own source.
		samefile_renames = set()
		for src in self._iter(self._files):
			dest = self._get_dest_url(src)
			if is_parent(src, dest, self._fs):
				if src != dest:
					try:
						is_samefile = self._fs.samefile(src, dest)
					except OSError:
						is_samefile = False
					if is_samefile:
						if self._can_transfer_samefile():
							samefile_renames.add(src)
							continue
				self.show_alert(
					"You cannot %s a file to itself." % self._descr_verb
				)
				return False
		dest_dir_url = self._get_dest_dir_url()
		try:
			self._fs.makedirs(dest_dir_url, exist_ok=True)
		except OSError as e:
			self.show_alert(
				'Could not create the destination folder %s (%s).' %
				(as_human_readable(dest_dir_url), _describe_error(e))
			)
			return False
		for i, src in enumerate(self._iter(self._files)):
			is_last = i == len(self._files) - 1
			dest = self._get_dest_url(src)
			if src in samefile_renames:
				self._enqueue(self._prepare_transfer(src, dest))
				continue
			try:
				is_dir = self._fs.is_dir(src)
			except OSError as e:
				error_message = 'Could not %s %s' % \
								(self._descr_verb, as_human_readable(src))
				if self._handle_exception(error_message, is_last, e):
					continue
				return False
			if is_dir:
				if self._fs.exists(dest):
					if not self._merge_directory(src):
						return False
				else:
					self._enqueue(self._prepare_transfer(src, dest))
			else:
				if self._fs.exists(dest):
					should_overwrite = self._should_overwrite(dest)
					if should_overwrite == NO:
						continue
					elif should_overwrite == ABORT:
						return False
					else:
						assert should_overwrite == YES, should_overwrite
				self._enqueue(self._prepare_transfer(src, dest))
		return True
	def _merge_directory(self, src):
		for file_name in self._fs.iterdir(src):
			file_url = join(src, file_name)
			try:
				src_is_dir = self._fs.is_dir(file_url)
			except OSError:
				src_is_dir = False
			dst = self._get_dest_url(file_url)
			if src_is_dir:
				try:
					dst_is_dir = self._fs.is_dir(dst)
				except OSError:
					dst_is_dir = False
				if dst_is_dir:
					if not self._merge_directory(file_url):
						return False
				else:
					self._enqueue(self._prepare_transfer(file_url, dst))
			else:
				if self._fs.exists(dst):
					should_overwrite = self._should_overwrite(dst)
					if should_overwrite == NO:
						continue
					elif should_overwrite == ABORT:
						return False
					else:
						assert should_overwrite == YES, \
							should_overwrite
				self._enqueue(self._prepare_transfer(file_url, dst))
		if self._does_postprocess_directory():
			# Post-process the parent directories bottom-up. For Move, this
			# ensures that each directory is empty when post-processing.
			self._enqueue([self._postprocess_directory(src)])
		return True
	def _should_overwrite(self, file_url):
		with self._alert_lock:
			return self._ask_overwrite(file_url)
	def _ask_overwrite(self, file_url):
		if self._override_all is None:
			choice = self.show_alert(
				"%s exists. Do you want to overwrite it?" % basename(file_url),
				YES | NO | YES_TO_ALL | NO_TO_ALL | ABORT, YES
			)
			if choice & YES:
				return YES
			elif choice & NO:
				return NO
			elif choice & YES_TO_ALL:
				self._override_all = True
			elif choice & NO_TO_ALL:
				self._override_all = False
			else:
				assert choice & ABORT, choice
				return ABORT
		return YES if self._override_all else NO
	def _enqueue(self, tasks):
		# Iterated lazily: a file system's prepare_copy(...) may walk a whole
		# tree, and each task must reach the transferring thread when found.
		for task in self._iter(tasks):
			self._queue.put(task)
	def _handle_exception(self, message, is_last, exc):
		with self._alert_lock:
			return self._ask_continue(message, is_last, exc)
	def _ask_continue(self, message, is_last, exc):
		if self._ignore_exceptions:
			return True
		cause = _describe_error(exc)
		message = '%s (%s).' % (message, cause)
		if is_last:
			buttons = OK
			default_button = OK
		else:
			buttons = YES | YES_TO_ALL | ABORT
			default_button = YES
			message += ' Do you want to continue?'
		choice = self.show_alert(message, buttons, default_button)
		if is_last:
			# The last task has no continue choice; an error still stops the move.
			self._ended_early = True
			return choice & OK
		else:
			if choice & YES_TO_ALL:
				self._ignore_exceptions = True
			continue_transfer = choice & YES or choice & YES_TO_ALL
			if not continue_transfer:
				self._ended_early = True
			return continue_transfer
	def _get_dest_dir_url(self):
		try:
			splitscheme(self._dest_dir)
		except ValueError:
			is_url = False
		else:
			is_url = True
		return self._dest_dir if is_url else join(self._src_dir, self._dest_dir)
	def _get_dest_url(self, src_file):
		dest_name = self._dest_name or basename(src_file)
		if self._src_dir:
			try:
				rel_path = \
					relpath(join(dirname(src_file), dest_name), self._src_dir)
			except ValueError as e:
				raise ValueError(
					'Could not construct path. '
					'src_file: %r, dest_name: %r, src_dir: %r' %
					(src_file, dest_name, self._src_dir)
				) from e
			is_in_src_dir = not rel_path.startswith(pardir)
			if is_in_src_dir:
				try:
					splitscheme(self._dest_dir)
				except ValueError:
					return join(self._src_dir, self._dest_dir, rel_path)
				else:
					return join(self._dest_dir, rel_path)
		return join(self._dest_dir, dest_name)
	def _iter(self, iterable):
		for item in iterable:
			self.check_canceled()
			if self._stop_gathering:
				# The transfers ended early (abort, error): stop walking.
				raise Task.Canceled()
			yield item
	def _get_title(self, descr_verb, files):
		verb = descr_verb.capitalize()
		result = (verb[:-1] if verb.endswith('e') else verb) + 'ing '
		if len(files) == 1:
			result += basename(files[0])
		else:
			result += '%d files' % len(files)
		return result

class CopyFiles(FileTreeOperation):
	def __init__(self, *super_args, **super_kwargs):
		super().__init__('copy', *super_args, **super_kwargs)
	def _transfer(self, src, dest):
		self._fs.copy(src, dest)
	def _can_transfer_samefile(self):
		# Can never copy to the same file.
		return False
	def _prepare_transfer(self, src, dest):
		return self._fs.prepare_copy(src, dest)

class MoveFiles(FileTreeOperation):
	def __init__(self, *super_args, **super_kwargs):
		super().__init__('move', *super_args, **super_kwargs)
		self._rollback = MoveRollback()
	def __call__(self):
		dest_dir = self._get_dest_dir_url()
		if not self._fs.exists(dest_dir):
			self._rollback.add_new_destination(dest_dir)
		try:
			super().__call__()
		except BaseException:
			self._run_rollback()
			raise
		if self._ended_early or self._gather_aborted or self._gather_canceled:
			self._run_rollback()
	def _on_task_done(self, task):
		self._rollback.record(task)
	def _run_rollback(self):
		self.set_text('Moving files back...')
		failed_urls = self._rollback.run(self._fs)
		if failed_urls:
			failed_names = [as_human_readable(url) for url in failed_urls[:10]]
			message = 'Could not move these files back:\n' + '\n'.join(failed_names)
			remaining = len(failed_urls) - len(failed_names)
			if remaining:
				message += '\n... and %d more.' % remaining
			self.show_alert(message)
	def _transfer(self, src, dest):
		self._fs.move(src, dest)
	def _can_transfer_samefile(self):
		# May be able to move to the same file on case insensitive file systems.
		# Consider a/ and A/: They are the "same" file yet it does make sense to
		# rename one to the other.
		return True
	def _prepare_transfer(self, src, dest):
		if self._fs.is_dir(src) and not self._fs.exists(dest):
			self._rollback.add_new_destination(dest)
		return self._fs.prepare_move(src, dest)
	def _does_postprocess_directory(self):
		return True
	def _postprocess_directory(self, src_dir_path):
		result = Task(
			'Postprocessing ' + basename(src_dir_path),
			fn=self._do_postprocess_directory, args=(src_dir_path,)
		)
		# The directory is only empty once the moves out of it are done.
		result.waits_for_earlier_tasks = True
		return result
	def _do_postprocess_directory(self, src_dir_path):
		if self._is_empty(src_dir_path):
			try:
				self._fs.delete(src_dir_path)
			except OSError:
				pass
	def _is_empty(self, dir_url):
		try:
			next(iter(self._fs.iterdir(dir_url)))
		except StopIteration:
			return True
		return False
