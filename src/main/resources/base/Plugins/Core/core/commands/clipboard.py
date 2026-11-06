"""The clipboard commands: Copy, Cut, Paste and clipboard text actions.

Copy/Cut only put the files *on* the clipboard - the actual work happens in
Paste, which dispatches to the `copy` or `move` command depending on which of
the two filled it. "Copy paths to clipboard" is the odd one out: it copies
text, not files, so it never takes part in that hand-off.

Copy file name and Copy file path copy one item's name or path as text.
"""
from fman import ApplicationCommand, clipboard, DirectoryPaneCommand, \
	PLATFORM, show_alert, show_status_message
from fman.fs import exists
from fman.url import as_human_readable, basename
from fman.impl.virtual_files import get_clipboard_data_object, \
	has_virtual_files, save_virtual_files
from core.commands.util import NO_SELECTION
from core.settings import SETTINGS_FILE, get_setting, save_setting

_COPY_PATHS_WITH_FORWARD_SLASHES_SETTING = 'copy_paths_with_forward_slashes'

__all__ = [
	'CopyFileName', 'CopyFilePath', 'CopyPathsToClipboard',
	'ToggleCopyPathsWithForwardSlashes', 'CopyToClipboard',
	'Cut', 'Paste', 'PasteCut'
]

class CopyPathsToClipboard(DirectoryPaneCommand):
	usable_in_viewer = True

	def __call__(self):
		to_copy = self.get_chosen_files() or [self.pane.get_path()]
		paths = list(map(as_human_readable, to_copy))
		if get_setting(
			SETTINGS_FILE, _COPY_PATHS_WITH_FORWARD_SLASHES_SETTING, False
		) is True:
			paths = [path.replace('\\', '/') for path in paths]
		clipboard.clear()
		clipboard.set_text('\n'.join(paths))
		_report_clipboard_action('Copied', to_copy, ' to the clipboard', 'path')

class ToggleCopyPathsWithForwardSlashes(ApplicationCommand):
	aliases = ('Toggle forward slashes when copying paths',)

	def __call__(self):
		enabled = get_setting(
			SETTINGS_FILE, _COPY_PATHS_WITH_FORWARD_SLASHES_SETTING, False
		) is not True
		save_setting(
			SETTINGS_FILE, _COPY_PATHS_WITH_FORWARD_SLASHES_SETTING, enabled
		)
		state = 'enabled' if enabled else 'disabled'
		show_status_message(
			'Forward slashes when copying paths are ' + state,
			timeout_secs=3
		)

class CopyFileName(DirectoryPaneCommand):
	usable_in_viewer = True

	def __call__(self):
		_copy_single_item_text(self.get_chosen_files(), basename)
	def is_visible(self):
		return len(self.get_chosen_files()) == 1

class CopyFilePath(DirectoryPaneCommand):
	usable_in_viewer = True

	def __call__(self):
		_copy_single_item_text(self.get_chosen_files(), as_human_readable)
	def is_visible(self):
		return len(self.get_chosen_files()) == 1

def _report_clipboard_action(verb, files, suffix='', ftype='file'):
	num = len(files)
	first_file = as_human_readable(files[0])
	if num == 1:
		message = '%s %s%s' % (verb, first_file, suffix)
	else:
		plural = 's' if num > 2 else ''
		message = '%s %s and %d other %s%s%s' % \
				  (verb, first_file, num - 1, ftype, plural, suffix)
	show_status_message(message, timeout_secs=3)

def _copy_single_item_text(files, format_text):
	if len(files) != 1:
		return
	text = format_text(files[0])
	clipboard.clear()
	clipboard.set_text(text)
	show_status_message('Copied %s to the clipboard' % text, timeout_secs=3)

class CopyToClipboard(DirectoryPaneCommand):
	def __call__(self):
		files = self.get_chosen_files()
		if files:
			clipboard.copy_files(files)
			_report_clipboard_action('Copying', files)
		else:
			show_alert(NO_SELECTION)
	def is_visible(self):
		return bool(self.pane.get_file_under_cursor())

class Cut(DirectoryPaneCommand):
	def __call__(self):
		if PLATFORM == 'Mac':
			show_alert(
				"Sorry, macOS doesn't support cutting files. Please press "
				"⌘-C (copy) followed by ⌘-⌥-V (move)."
			)
			return
		files = self.get_chosen_files()
		if files:
			clipboard.cut_files(files)
			_report_clipboard_action('Cutting', files)
		else:
			show_alert(NO_SELECTION)
	def is_visible(self):
		return bool(self.pane.get_file_under_cursor())

class Paste(DirectoryPaneCommand):
	def __call__(self):
		files = clipboard.get_files()
		if not files:
			data_object = get_clipboard_data_object()
			if not has_virtual_files(data_object):
				return
			files = save_virtual_files(data_object)
		elif clipboard.files_were_cut():
			self.pane.run_command('paste_cut')
			return
		dest = self.pane.get_path()
		self.pane.run_command('copy', {'files': files, 'dest_dir': dest})
	def is_visible(self):
		return bool(clipboard.get_files()) or has_virtual_files(
			get_clipboard_data_object())

class PasteCut(DirectoryPaneCommand):
	def __call__(self):
		files = clipboard.get_files()
		if not any(map(exists, files)):
			# This can happen when the paste-cut has already been performed.
			return
		dest_dir = self.pane.get_path()
		self.pane.run_command('move', {
			'files': files,
			'dest_dir': dest_dir
		})
