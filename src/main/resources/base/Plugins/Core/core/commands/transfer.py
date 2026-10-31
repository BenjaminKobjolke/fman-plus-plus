"""Moving files somewhere else: copy, move, symlink, drag-and-drop.

All of them ask the same question first - "to where?" - so they share
`_TreeCommand`, which resolves the answer (relative paths, existing
directories, overwriting a single file) before any file is touched.
Packing asks it too, through `get_dest_suggestion` - see
core/commands/pack.py.
"""
# `import *` skips underscore names: get_dest_suggestion splits the extension
# off the name it suggests, the same way the editor's "New file" prompt does.
from core import elevation
from core.commands.editor import _find_extension_start
from core.commands.util import get_opposite_pane, is_file_url, \
	CANNOT_READ, NO_SELECTION
from core.commands.deselect_after_transfer import is_enabled as \
	deselect_after_transfer_enabled
from core.fileoperations import CopyFiles, MoveFiles
from core.path_completion import complete_path
from core.util import is_parent
from core.undo_history import CopyRecord, MoveRecord, record_transfer
from fman import DirectoryPaneCommand, DirectoryPaneListener, NO, YES, \
	YES_TO_ALL, show_alert, submit_task
from fman.fs import makedirs, notify_file_added
from fman.url import as_human_readable, join, splitscheme
# os.path.basename, not fman.url's: this is what core/commands/__init__.py
# used before this module existed (its later `from os.path import basename`
# shadowed the URL one for the whole file).
from os.path import basename
from pathlib import PurePath
from functools import partial

import fman
import fman.fs
import os
import re

__all__ = ['Copy', 'DragAndDropListener', 'Move', 'Symlink',
           'get_dest_suggestion']

class _TreeCommand(DirectoryPaneCommand):
	# Copy, Move and Symlink all operate on the viewed file.
	usable_in_viewer = True
	_files_from_selection = False

	def __call__(self, files=None, dest_dir=None):
		self._files_from_selection = files is None
		if files is None:
			files = self.get_chosen_files()
		if dest_dir is None:
			dest_dir = get_opposite_pane(self.pane).get_path()
		proceed = self._confirm_tree_operation(files, dest_dir)
		if proceed:
			dest_dir, dest_name = proceed
			transfers = tuple(
				(file_, join(dest_dir, dest_name or basename(file_)))
				for file_ in files
			)
			destinations_that_existed = {
				dest_url for _, dest_url in transfers
				if fman.fs.exists(dest_url)
			}
			if not self._call_elevated(files, dest_dir, dest_name):
				makedirs(dest_dir, exist_ok=True)
				self._call(files, dest_dir, dest_name)
			self._record_operation(
				transfers, destinations_that_existed
			)
	def _record_operation(self, transfers, destinations_that_existed):
		pass
	def _call(self, files, dest_dir, dest_name=None):
		raise NotImplementedError()
	def _call_elevated(self, files, dest_dir, dest_name):
		# Returns whether core.elevation took care of it - see there.
		return False
	@classmethod
	def _confirm_tree_operation(cls, files, dest_dir, ui=fman, fs=fman.fs):
		if not files:
			ui.show_alert(NO_SELECTION)
			return
		dest_path = as_human_readable(dest_dir)
		verb = cls._verb().capitalize()
		selection_end = None # Select everything
		exists_and_is_dir = False
		if len(files) == 1:
			file_, = files
			dest_name = basename(file_)
			try:
				exists_and_is_dir = fs.is_dir(file_)
			except FileNotFoundError:
				exists_and_is_dir = False
			except OSError as e:
				ui.show_alert(CANNOT_READ % (as_human_readable(file_), e))
				return
			if not exists_and_is_dir:
				selection_end = _find_extension_start(dest_name)
			message = '%s "%s" to\n%s' % (verb, dest_name, dest_path)
			suggested_dst = dest_name
		else:
			message = '%s %d files to' % (verb, len(files))
			suggested_dst = dest_path
		dest, ok = ui.show_prompt(
			message, suggested_dst, 0, selection_end,
			get_completions=partial(
				complete_path, dest_dir=dest_dir, src_dir=None, fs=fs
			)
		)
		if dest and ok:
			dest_url = _from_human_readable(dest, dest_dir, None)
			if fs.exists(dest_url):
				try:
					dest_is_dir = fs.is_dir(dest_url)
				except OSError as e:
					ui.show_alert(CANNOT_READ % (dest, e))
					return
				if dest_is_dir:
					if len(files) == 1 and fs.samefile(dest_url, files[0]):
						# This happens when renaming a/ -> A/ on
						# case-insensitive file systems.
						return _split(dest_url)
					if cls._is_into_itself(files, dest_url, ui, fs):
						return
					if exists_and_is_dir and \
						dest_url == join(dest_dir, dest_name):
						# The dir's own name, left as suggested: merge into
						# the existing dir of that name. Returning dest_url
						# would nest a second copy inside it.
						return dest_dir, None
					return dest_url, None
				else:
					if len(files) == 1:
						return _split(dest_url)
					else:
						ui.show_alert(
							'You cannot %s multiple files to a single file!' %
							cls._verb()
						)
			else:
				if len(files) == 1:
					if cls._is_into_itself(files, dest_url, ui, fs):
						return
					return _split(dest_url)
				else:
					choice = ui.show_alert(
						'%s does not exist. Do you want to create it '
						'as a directory and %s the files there?' %
						(as_human_readable(dest_url), cls._verb()),
						YES | NO, YES
					)
					if choice & YES:
						return dest_url, None
	@classmethod
	def _is_into_itself(cls, files, dest_url, ui, fs):
		for file_ in files:
			if is_parent(file_, dest_url, fs):
				ui.show_alert('You cannot %s a file to itself!' % cls._verb())
				return True
		return False
	@classmethod
	def _verb(cls):
		return cls.__name__.lower()
	def is_visible(self):
		return bool(self.pane.get_file_under_cursor())

def get_dest_suggestion(dst_url):
	scheme = splitscheme(dst_url)[0]
	if scheme == 'file://':
		sep = os.sep
		suggested_dst = as_human_readable(dst_url)
		offset = 0
	else:
		sep = '/'
		suggested_dst = dst_url
		offset = len(scheme)
	try:
		last_sep = suggested_dst.rindex(sep, offset)
	except ValueError:
		selection_start = offset
	else:
		selection_start = last_sep + 1
	selection_end = _find_extension_start(suggested_dst, selection_start)
	return suggested_dst, selection_start, selection_end

def _from_human_readable(path_or_url, dest_dir, src_dir):
	try:
		splitscheme(path_or_url)
	except ValueError:
		dest_scheme, dest_dir_path = splitscheme(dest_dir)
		if src_dir:
			# Treat dest as relative to src_dir:
			base_path = splitscheme(src_dir)[1]
		else:
			base_path = dest_dir_path
		if base_path.endswith(':'):
			# A drive root is 'C:' here. PurePath('C:', 'a') is 'C:a' - relative
			# to the drive's current directory, not to its root.
			base_path += '/'
		path_or_url = dest_scheme + PurePath(base_path, path_or_url).as_posix()
	return path_or_url

def _split(url):
	scheme, tail = splitscheme(url)
	head, tail = re.match('(/*)(.*?)$', tail).groups()
	if '/' in tail:
		h2, tail = tail.rsplit('/', 1)
		head += h2
	return scheme + head, tail

class Copy(_TreeCommand):
	def _call(self, files, dest_dir, dest_name=None):
		on_file_done = self._deselect if \
			self._files_from_selection and deselect_after_transfer_enabled() \
			else None
		submit_task(CopyFiles(
			files, dest_dir, dest_name, on_file_done=on_file_done
		))
	def _deselect(self, url):
		self.pane.deselect([url])
	def _call_elevated(self, files, dest_dir, dest_name):
		return elevation.copy(files, dest_dir, dest_name)
	def _record_operation(self, transfers, destinations_that_existed):
		record_transfer(
			CopyRecord, transfers, destinations_that_existed, fman.fs.exists
		)

class Move(_TreeCommand):
	def _call(self, files, dest_dir, dest_name=None):
		submit_task(MoveFiles(files, dest_dir, dest_name))
	def _call_elevated(self, files, dest_dir, dest_name):
		return elevation.move(files, dest_dir, dest_name)
	def _record_operation(self, transfers, destinations_that_existed):
		record_transfer(
			MoveRecord, transfers, destinations_that_existed, fman.fs.exists
		)

class DragAndDropListener(DirectoryPaneListener):
	def on_files_dropped(self, file_urls, dest_dir, is_copy_not_move):
		command = self._get_command(file_urls, dest_dir, is_copy_not_move)
		self.pane.run_command(
			command, {'files': file_urls, 'dest_dir': dest_dir}
		)
	def _get_command(self, file_urls, dest_dir, is_copy_not_move):
		schemes = set(splitscheme(url)[0] for url in file_urls)
		src_scheme = next(iter(schemes)) if len(schemes) == 1 else ''
		dest_scheme = splitscheme(dest_dir)[0]
		if src_scheme != dest_scheme:
			# The default value for `is_copy_not_move` is False. But consider
			# the case where the user drags a file from a Zip archive to the
			# local file system. In this case, `is_copy_not_move` might indicate
			# "move" simply because it's the default. But most likely, the user
			# simply wants to extract the file and not also remove it from the
			# Zip file. Respect this:
			is_copy_not_move = True
		return 'copy' if is_copy_not_move else 'move'

class Symlink(_TreeCommand):

	aliases = ('Symlink',)

	def is_visible(self):
		if not super().is_visible():
			return False
		return is_file_url(self.pane.get_path()) and \
			   is_file_url(get_opposite_pane(self.pane).get_path())

	def __call__(self):
		src_url = self.pane.get_path()
		if not is_file_url(src_url):
			self._refuse()
			return
		dest_url = get_opposite_pane(self.pane).get_path()
		if not is_file_url(dest_url):
			self._refuse()
			return
		super().__call__()

	def _call(self, files, dest_dir, dest_name=None):
		ignore_exists = False
		for i, f_url in enumerate(files):
			dest_url = join(dest_dir, dest_name or basename(f_url))
			if not is_file_url(f_url) or not is_file_url(dest_url):
				self._refuse()
				return
			f_path = as_human_readable(f_url)
			dest_path = as_human_readable(dest_url)
			try:
				os.symlink(f_path, dest_path, fman.fs.is_dir(f_url))
			except FileExistsError:
				if ignore_exists:
					continue
				has_more = i < len(files) - 1
				if has_more:
					answer = show_alert(
						"%s exists and cannot be symlinked. Continue?"
						% basename(f_url),
						YES | NO | YES_TO_ALL, YES
					)
					if answer & YES_TO_ALL:
						ignore_exists = True
					elif answer & NO:
						break
				else:
					show_alert(
						"%s exists and cannot be symlinked." % basename(f_url)
					)
			else:
				notify_file_added(dest_url)

	def _refuse(self):
		show_alert('Sorry, can only create symlinks between local files.')
