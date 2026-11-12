"""Renaming a file in place, and creating the directory to rename into.

`_Rename` is a Task rather than a straight prepare_move(...) so a failure can
offer Retry without the user retyping the new name - see its own comment.
"""
from core import elevation
from core.file_extension import name_with_hidden_extension
from core.commands.new_file import _find_extension_start
from core.commands import show_file_comment_error
from core.commands.util import (
	_fs_implements, create_as_admin, is_dir_checked, NO_SELECTION
)
from core.undo_history import RenameRecord, history
from core.descript_ion import move_comments
from core.util import is_relative_name
from functools import partial
from fman import CANCEL, DirectoryPaneCommand, DirectoryPaneListener, \
	PLATFORM, RETRY, show_alert, show_input, submit_task, Task
from fman.fs import exists, makedirs, prepare_move, samefile
from fman.url import dirname, join, normalize, relpath, splitscheme
# os.path.basename, not fman.url's, matching what core/commands/__init__.py
# resolved this name to before this module existed.
from os.path import basename
import fman.fs

__all__ = ['CreateDirectory', 'Rename', 'RenameListener']

class Rename(DirectoryPaneCommand):
	def __call__(self):
		file_under_cursor = self.pane.get_file_under_cursor()
		if file_under_cursor:
			file_is_dir = is_dir_checked(file_under_cursor)
			if file_is_dir is None:
				return
			if file_is_dir:
				selection_end = None
			else:
				file_name = basename(file_under_cursor)
				selection_end = _find_extension_start(file_name)
			self.pane.edit_name(
				file_under_cursor, selection_end=selection_end,
				callback=partial(_on_name_edited, self.pane)
			)
		else:
			show_alert(NO_SELECTION)
	def is_visible(self):
		return bool(self.pane.get_file_under_cursor())

class RenameListener(DirectoryPaneListener):
	def on_name_edited(self, file_url, new_name):
		# Kept for plugins that still call pane.edit_name(...) without a callback.
		_on_name_edited(self.pane, file_url, new_name)

def _on_name_edited(pane, file_url, new_name):
	# The editor only showed the stem while the extension column is enabled.
	rename_to(
		pane, file_url,
		name_with_hidden_extension(fman.fs, file_url, new_name)
	)

def rename_to(pane, file_url, new_name):
	"""
	Validates `new_name` and submits the rename, returning the new url - or
	None when there is nothing to do (unchanged name) or the name was
	rejected, in which case the user has already been told why.

	Split out of _on_name_edited so the in-pane viewers can
	rename the file they are showing (core/viewer_file_ops.py): the Rename
	command itself is unusable there, driving pane.edit_name on the file list
	the viewer is covering.
	"""
	old_name = basename(file_url)
	if not new_name or new_name == old_name:
		return None
	if not is_relative_name(new_name):
		show_alert(
			'Relative paths are not supported. Please use Move (F6) '
			'instead.'
		)
		return None
	new_url = join(dirname(file_url), new_name)
	if exists(new_url):
		# Don't show dialog when "Foo" was simply renamed to "foo":
		if not samefile(new_url, file_url):
			show_alert(new_name + ' already exists!')
			return None
	if elevation.rename(file_url, new_name):
		_place_cursor_at(pane, new_url)
		_record_rename(file_url, new_url)
	else:
		submit_task(_Rename(pane, file_url, new_url))
	return new_url

def _record_rename(src_url, dst_url):
	history.record(RenameRecord(((src_url, dst_url),)))
	try:
		move_comments(((src_url, dst_url),))
	except OSError as error:
		show_file_comment_error(error)

def _place_cursor_at(pane, url):
	try:
		pane.place_cursor_at(url)
	except ValueError:
		pass

class _Rename(Task):
	def __init__(self, pane, src_url, dst_url):
		self._pane = pane
		self._src_url = src_url
		self._dst_url = dst_url
		super().__init__('Renaming ' + basename(src_url))
	def __call__(self):
		# Loop so the alert below can offer Retry: the usual cause of a failure
		# is another program holding the file open. The user closes it and
		# retries without having to retype the new name. prepare_move(...) is
		# re-run per attempt because the tasks it yields are single-use.
		while True:
			self.set_text('Preparing...')
			self.set_progress(0)
			tasks = list(prepare_move(self._src_url, self._dst_url))
			self.set_size(sum(t.get_size() for t in tasks))
			try:
				for task in tasks:
					self.check_canceled()
					self.run(task)
			except OSError as e:
				if isinstance(e, PermissionError):
					message = 'Access was denied trying to rename %s to %s.'
				else:
					message = 'Could not rename %s to %s.'
				old_name = basename(self._src_url)
				new_name = basename(self._dst_url)
				message %= (old_name, new_name)
				# Escape returns 0, which is falsy here - so it cancels:
				if self.show_alert(message, RETRY | CANCEL, RETRY) & RETRY:
					continue
				return
			_place_cursor_at(self._pane, self._dst_url)
			_record_rename(self._src_url, self._dst_url)
			return

class CreateDirectory(DirectoryPaneCommand):

	aliases = ('New folder',)

	def __call__(self):
		name = show_input("New folder (directory)")
		if name:
			# Support recursive creation of directories:
			if PLATFORM == 'Windows':
				name = name.replace('\\', '/')
			base_url = self.pane.get_path()
			dir_url = join(base_url, name)
			try:
				makedirs(dir_url)
			except FileExistsError:
				show_alert("A file with this name already exists!")
			except PermissionError as e:
				if not create_as_admin(dir_url, is_dir=True, error=e):
					return
			# Use normalize(...) instead of resolve(...) to avoid the following
			# problem: Say c/ is a symlink to a/b/. We're inside c/ and create
			# d. Then # resolve(c/d) would give a/b/d and the relative path
			# further down # would be ../a/b/d. We could not place the cursor at
			# that. If on # the other hand, we use normalize(...), then we
			# compute the relpath from c -> c/d, which does work.
			effective_url = normalize(dir_url)
			select = relpath(effective_url, base_url).split('/')[0]
			if select != '..':
				_place_cursor_at(self.pane, join(base_url, select))
	def is_visible(self):
		fs = splitscheme(self.pane.get_path())[0]
		return _fs_implements(fs, 'mkdir')
