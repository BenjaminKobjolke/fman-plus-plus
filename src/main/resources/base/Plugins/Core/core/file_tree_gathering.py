"""Gather files and prepare their transfer tasks."""
from core.util import is_parent
from fman import Task, YES, NO, YES_TO_ALL, NO_TO_ALL, ABORT, OK
from fman.url import basename, join, dirname, splitscheme, relpath, \
	as_human_readable
from os.path import pardir


def describe_error(error):
	# Providers may wrap the OS error, e.g. FileExistsError(path) from WinError 183.
	for candidate in (error, error.__cause__):
		strerror = getattr(candidate, 'strerror', None)
		if strerror:
			return strerror[0].lower() + strerror[1:]
	return error.__class__.__name__


class FileTreeGathering:
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
				(as_human_readable(dest_dir_url), describe_error(e))
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
		cause = describe_error(exc)
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
