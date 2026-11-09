"""Use Windows' `runas` shell verb to show UAC and launch local files elevated."""
from core.commands.util import is_dir_checked, is_file_url, NO_SELECTION
from fman import DirectoryPaneCommand, PLATFORM, show_alert
from fman.fs import resolve
from fman.url import as_human_readable, splitscheme

import os

__all__ = ['RunAsAdministrator']

_CANNOT_RUN_FOLDER = 'Cannot run a folder as administrator.'
_UNSUPPORTED_SCHEME = 'Sorry, running %s files is not supported.'
_COULD_NOT_RUN = 'Could not run %s as administrator:\n%s'


class RunAsAdministrator(DirectoryPaneCommand):
	aliases = ('Run as administrator',)

	def __call__(self):
		urls = self.get_chosen_files()
		if not urls:
			show_alert(NO_SELECTION)
			return
		for url in urls:
			try:
				resolved_url = resolve(url)
			except OSError:
				continue
			scheme, _ = splitscheme(resolved_url)
			if scheme != 'file://':
				show_alert(_UNSUPPORTED_SCHEME % scheme)
				return
			is_dir = is_dir_checked(resolved_url)
			if is_dir is None:
				continue
			if is_dir:
				show_alert(_CANNOT_RUN_FOLDER)
				continue
			self._run_elevated(as_human_readable(resolved_url))

	def _run_elevated(self, path):
		from win32api import ShellExecute
		from win32con import SW_SHOWNORMAL
		import pywintypes
		from winerror import ERROR_CANCELLED
		try:
			ShellExecute(
				0, 'runas', path, None, os.path.dirname(path), SW_SHOWNORMAL
			)
		except pywintypes.error as e:
			if e.winerror != ERROR_CANCELLED:
				show_alert(_COULD_NOT_RUN % (path, e.strerror))

	def is_visible(self):
		return (
			PLATFORM == 'Windows'
			and is_file_url(self.pane.get_path())
			and bool(self.pane.get_file_under_cursor())
		)
