"""Packing the chosen files into a new archive.

The destination prompt is the transfer one (`get_dest_suggestion`), but the
archive itself is created by the filesystem registered for the suffix the
user typed - so 'x.7z' and 'x.zip' end up handled by different filesystems,
and a suffix nobody registered is refused before any file is read.
"""
from core.commands.archives import _get_handler_for_archive
from core.commands.deletion import _describe
from core.fs import archive_password
from core.path_completion import complete_path
from core.commands.transfer import _from_human_readable, get_dest_suggestion
from core.commands.util import chosen_files, get_opposite_pane
from fman import DirectoryPaneCommand, NO, Task, YES, show_alert, \
	show_input, submit_task
from fman.fs import mkdir, notify_file_changed, prepare_copy
from fman.url import as_url, dirname, join, splitscheme
# os.path.basename, not fman.url's - see core/commands/transfer.py.
from os.path import basename
from pathlib import PurePath
from functools import partial

import fman.fs
import re

__all__ = ['Pack', 'PackHere', 'PackWithPassword']

# Suggested when the pane's directory has no name of its own ('drives://').
_DEFAULT_ARCHIVE_NAME = 'archive'
_PASSWORD_PACK_ALIAS = 'Pack to archive with password (.zip, .7z)'
_PASSWORD_PACK_PROMPT = 'Pack %s to password-protected (.zip, .7z):'
_PASSWORD_PROMPT = 'Password:'
_CONFIRM_PASSWORD_PROMPT = 'Confirm password:'
_PASSWORD_MISMATCH_MESSAGE = 'The passwords do not match.'
_TAR_PASSWORD_MESSAGE = 'Tar archives cannot be password-protected.'
_NON_ASCII_ZIP_MESSAGE = (
	'Zip archives do not support non-ASCII passwords in 7-Zip. '
	'Choose a .7z archive instead.'
)

class Pack(DirectoryPaneCommand):

	aliases = ('Pack to archive (.zip, .7z, .tar)',)
	usable_in_viewer = True

	def __call__(self):
		files = chosen_files(self)
		if not files:
			return
		if len(files) == 1:
			dest_name = PurePath(basename(files[0])).stem + '.zip'
		else:
			dest_name = _suggest_archive_name(self.pane.get_path())
		dest_dir = self._get_dest_dir()
		dest_url = join(dest_dir, dest_name)
		suggested_dst, selection_start, selection_end = \
			get_dest_suggestion(dest_url)
		dest = show_input(
			self._get_prompt(files), suggested_dst,
			selection_start, selection_end,
			get_completions=partial(
				complete_path, dest_dir=dest_dir,
				src_dir=self.pane.get_path(), fs=fman.fs
			)
		)
		if dest:
			dest = _from_human_readable(dest, dest_dir, self.pane.get_path())
			scheme = _get_handler_for_archive(basename(dest))
			if not scheme:
				show_alert('Sorry, but this archive format is not supported.')
				return
			dest_rewritten = scheme + splitscheme(dest)[1]
			password = self._prepare_password(dest_rewritten)
			if password is False:
				return
			try:
				# Create empty archive:
				mkdir(dest_rewritten)
			except FileExistsError:
				answer = show_alert(
					'%s already exists. Do you want to add/update the selected '
					'files?' % basename(dest_rewritten), YES | NO, YES
				)
				if not answer & YES:
					return
			if password is not None:
				archive_password.remember_password(
					splitscheme(dest_rewritten)[1], password
				)
			submit_task(_Pack(files, dest_rewritten))
	def _get_prompt(self, files):
		return 'Pack %s to (.zip, .7z, .tar):' % _describe(files)
	def _get_dest_dir(self):
		return get_opposite_pane(self.pane).get_path()
	def _prepare_password(self, archive_url):
		return None
	def is_visible(self):
		return bool(self.pane.get_file_under_cursor())

class PackHere(Pack):
	aliases = ('Pack here', 'Compress here')
	def _get_dest_dir(self):
		return self.pane.get_path()

class PackWithPassword(Pack):
	aliases = (_PASSWORD_PACK_ALIAS,)
	def _get_prompt(self, files):
		return _PASSWORD_PACK_PROMPT % _describe(files)
	def _prepare_password(self, archive_url):
		file_name = basename(archive_url).lower()
		if file_name.endswith(('.tar', '.tar.gz', '.tar.bz2', '.tar.xz')):
			show_alert(_TAR_PASSWORD_MESSAGE)
			return False
		password = show_input(_PASSWORD_PROMPT, '', password=True)
		if password is None:
			return False
		confirmation = show_input(
			_CONFIRM_PASSWORD_PROMPT, '', password=True
		)
		if confirmation is None:
			return False
		if password != confirmation:
			show_alert(_PASSWORD_MISMATCH_MESSAGE)
			return False
		if file_name.endswith('.zip') and not password.isascii():
			show_alert(_NON_ASCII_ZIP_MESSAGE)
			return False
		return password

def _suggest_archive_name(dir_url):
	scheme, path = splitscheme(dir_url)
	path = path.rstrip('/')
	if scheme == 'file://' and re.fullmatch('[A-Za-z]:', path):
		# A drive root: 'C:.zip' is not a valid file name.
		name = path[0]
	else:
		name = basename(scheme + path)
	return (name or _DEFAULT_ARCHIVE_NAME) + '.zip'

class _Pack(Task):
	def __init__(self, files, archive_url):
		super().__init__('Packing ' + _describe(files), size=len(files) * 100)
		self._files = files
		self._archive = archive_url
	def __call__(self):
		try:
			for f in self._files:
				for task in prepare_copy(f, join(self._archive, basename(f))):
					self.check_canceled()
					self.run(task)
		finally:
			# Archive filesystems notify their scheme; Windows lacks folder watching.
			notify_file_changed(dirname(as_url(splitscheme(self._archive)[1])))
