from core.transfer_workers import DONE, TransferWorkers, WorkerProgress
from core.file_tree_gathering import FileTreeGathering
from fman import Task
from fman.url import basename, dirname, as_human_readable
from queue import Queue
from threading import Lock, Thread
from urllib.parse import urlparse
from core.move_rollback import MoveRollback
from core.transfer_completion import TransferCompletion

import fman.fs

class FileTreeOperation(FileTreeGathering, Task):
	minimizable = True

	def __init__(
		self, descr_verb, files, dest_dir, dest_name=None, fs=fman.fs,
		on_file_done=None
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
		self._completion = TransferCompletion(
			on_file_done or (lambda url: None)
		)
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
	def _get_connection_count(self):
		# A filesystem hook counts a whole server, so do not ask twice for one.
		urls = {
			urlparse(url)[:2]: url
			for url in (self._files[0], self._get_dest_dir_url())
		}
		counts = [
			self._fs.get_connection_count(url) for url in urls.values()
		]
		counts = [count for count in counts if count is not None]
		return sum(counts) if counts else None
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
			should_stop=lambda: self._gather_aborted,
			connection_count=self._get_connection_count
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
			self._completion.task_finished(task, False)
			title = task.get_title()
			message = 'Error ' + (title[0].lower() + title[1:])
			if not self._handle_exception(message, is_last, e):
				return False
			progress.set_progress(size)
		else:
			self._completion.task_finished(task, True)
			self._on_task_done(task)
		finally:
			worker.title = ''
		return True
	def _on_task_done(self, task):
		pass

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
