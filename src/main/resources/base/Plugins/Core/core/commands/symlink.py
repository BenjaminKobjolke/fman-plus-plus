"""Create links between local files."""
from core.commands.transfer import _TreeCommand
from core.commands.util import get_opposite_pane, is_file_url
from fman import NO, YES, YES_TO_ALL, show_alert
from fman.fs import notify_file_added
from fman.url import as_human_readable, join
from os.path import basename

import fman.fs
import os

__all__ = ['Symlink']


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
