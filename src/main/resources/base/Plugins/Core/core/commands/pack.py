"""Packing the chosen files into a new archive.

The destination prompt is the transfer one (`get_dest_suggestion`), but the
archive itself is created by the filesystem registered for the suffix the
user typed - so 'x.7z' and 'x.zip' end up handled by different filesystems,
and a suffix nobody registered is refused before any file is read.
"""
from core.commands.archives import _get_handler_for_archive
from core.commands.deletion import _describe
from core.path_completion import complete_path
from core.commands.transfer import _from_human_readable, get_dest_suggestion
from core.commands.util import chosen_files, get_opposite_pane
from fman import DirectoryPaneCommand, NO, Task, YES, show_alert, \
	show_prompt, submit_task
from fman.fs import mkdir, prepare_copy
from fman.url import join, splitscheme
# os.path.basename, not fman.url's - see core/commands/transfer.py.
from os.path import basename
from pathlib import PurePath
from functools import partial

import fman.fs
import re

__all__ = ['Pack']

# Suggested when the pane's directory has no name of its own ('drives://').
_DEFAULT_ARCHIVE_NAME = 'archive'

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
		dest_dir = get_opposite_pane(self.pane).get_path()
		dest_url = join(dest_dir, dest_name)
		suggested_dst, selection_start, selection_end = \
			get_dest_suggestion(dest_url)
		dest, ok = show_prompt(
			'Pack %s to (.zip, .7z, .tar):' % _describe(files), suggested_dst,
			selection_start, selection_end,
			get_completions=partial(
				complete_path, dest_dir=dest_dir,
				src_dir=self.pane.get_path(), fs=fman.fs
			)
		)
		if dest and ok:
			dest = _from_human_readable(dest, dest_dir, self.pane.get_path())
			scheme = _get_handler_for_archive(basename(dest))
			if not scheme:
				show_alert('Sorry, but this archive format is not supported.')
				return
			dest_rewritten = scheme + splitscheme(dest)[1]
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
			submit_task(_Pack(files, dest_rewritten))
	def is_visible(self):
		return bool(self.pane.get_file_under_cursor())

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
		for f in self._files:
			for task in prepare_copy(f, join(self._archive, basename(f))):
				self.check_canceled()
				self.run(task)
