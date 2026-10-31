"""Gather files and prepare their transfer tasks."""
from core.overwrite_details import free_name, get_details
from core.util import is_parent, is_relative_name
from fman import Task, OK, YES, YES_TO_ALL, ABORT
from fman.impl.overwrite_dialog import OverwriteChoice
from fman.url import basename, join, dirname, splitscheme, relpath, \
	as_human_readable
from os.path import pardir, splitext


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
			self._completion.begin_item(src)
			if not self._gather_item(src, is_last, samefile_renames):
				return False
			self._completion.end_item()
		return True
	def _gather_item(self, src, is_last, samefile_renames):
		dest = self._get_dest_url(src)
		if src in samefile_renames:
			self._enqueue(self._prepare_transfer(src, dest))
			return True
		try:
			is_dir = self._fs.is_dir(src)
		except OSError as e:
			error_message = 'Could not %s %s' % \
							(self._descr_verb, as_human_readable(src))
			if self._handle_exception(error_message, is_last, e):
				self._completion.mark_incomplete()
				return True
			return False
		if is_dir:
			if self._fs.exists(dest):
				return self._merge_directory(src)
			self._enqueue(self._prepare_transfer(src, dest))
		else:
			dest = self._resolve_conflict(src, dest)
			if dest is OverwriteChoice.ABORT:
				return False
			if dest is None:
				self._completion.mark_incomplete()
				return True
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
				dst = self._resolve_conflict(file_url, dst)
				if dst is OverwriteChoice.ABORT:
					return False
				if dst is None:
					self._completion.mark_incomplete()
					continue
				self._enqueue(self._prepare_transfer(file_url, dst))
		if self._does_postprocess_directory():
			# Post-process the parent directories bottom-up. For Move, this
			# ensures that each directory is empty when post-processing.
			self._enqueue([self._postprocess_directory(src)])
		return True
	def _is_taken(self, dest):
		return self._fs.exists(dest) or dest in self._reserved_dests
	def _resolve_conflict(self, src, dest):
		if not self._is_taken(dest):
			return dest
		with self._alert_lock:
			return self._ask_overwrite(src, dest)
	def _ask_overwrite(self, src, dest):
		if self._conflict_policy == OverwriteChoice.RENAME:
			return self._reserve_renamed_dest(dest)
		if self._conflict_policy == OverwriteChoice.SKIP:
			return None
		if self._conflict_policy == OverwriteChoice.OVERWRITE:
			return dest
		choice = self.show_overwrite_dialog(
			'%s exists. Do you want to overwrite it?' % basename(dest),
			get_details(self._fs, src, dest)
		)
		if choice == OverwriteChoice.OVERWRITE:
			return dest
		if choice == OverwriteChoice.OVERWRITE_ALL:
			self._conflict_policy = OverwriteChoice.OVERWRITE
			return dest
		if choice == OverwriteChoice.SKIP:
			return None
		if choice == OverwriteChoice.SKIP_ALL:
			self._conflict_policy = OverwriteChoice.SKIP
			return None
		if choice == OverwriteChoice.RENAME_ALL:
			self._conflict_policy = OverwriteChoice.RENAME
			return self._reserve_renamed_dest(dest)
		if choice == OverwriteChoice.RENAME:
			return self._ask_new_name(src, dest)
		assert choice == OverwriteChoice.ABORT, choice
		return OverwriteChoice.ABORT
	def _reserve_renamed_dest(self, dest):
		new_dest = free_name(dest, self._is_taken)
		self._record_renamed_dest(dest, new_dest)
		return new_dest
	def _record_renamed_dest(self, dest, new_dest):
		self._reserved_dests.add(new_dest)
		if any(self._get_dest_url(src) == dest for src in self._files):
			self.renamed_dests[dest] = new_dest
	def _ask_new_name(self, src, dest):
		default = basename(free_name(dest, self._is_taken))
		stem, _extension = splitext(default)
		while True:
			name, accepted = self.show_prompt(
				'Enter a new name for %s:' % basename(dest), default,
				0, len(stem)
			)
			if not accepted:
				return self._ask_overwrite(src, dest)
			if not name or name in ('.', '..') or not is_relative_name(name):
				self.show_alert('Please enter a valid file name.')
				continue
			new_dest = join(dirname(dest), name)
			if self._is_taken(new_dest):
				self.show_alert('%s already exists.' % name)
				continue
			self._record_renamed_dest(dest, new_dest)
			return new_dest
	def _enqueue(self, tasks):
		# Iterated lazily: a file system's prepare_copy(...) may walk a whole
		# tree, and each task must reach the transferring thread when found.
		for task in self._iter(tasks):
			self._completion.add_task(task)
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
