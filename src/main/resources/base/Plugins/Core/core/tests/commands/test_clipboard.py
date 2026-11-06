from core.commands.clipboard import (
	CopyPathsToClipboard, CopyToClipboard, Cut, Paste,
	ToggleCopyPathsWithForwardSlashes, _report_clipboard_action,
)
from core.commands.util import NO_SELECTION
from core.tests.commands import FakePane
from fman import DirectoryPane
from fman.url import as_human_readable, as_url
from unittest import TestCase
from unittest.mock import Mock, patch

class CopyItemTextTest(TestCase):
	def test_single_selected_items_copy_name_or_path(self):
		items = [
			('file://C:/folder/report.tar.gz', 'report.tar.gz'),
			('file://C:/folder/My Folder', 'My Folder'),
			('file://C:/folder/café.txt', 'café.txt'),
			('file:////server/share/Folder', 'Folder'),
			('zip://C:/archive.zip/folder/item.txt', 'item.txt')
		]
		for url, name in items:
			with self.subTest(url=url):
				self._assert_copy(url, name, 'CopyFileName')
				self._assert_copy(
					url, as_human_readable(url), 'CopyFilePath'
				)

	def test_cursor_fallback_and_invalid_counts(self):
		url = 'file://C:/folder/report.txt'
		for command_name in ('CopyFileName', 'CopyFilePath'):
			command_class = self._command_class(command_name)
			with self.subTest(command=command_name, case='cursor fallback'):
				pane = Mock(spec=DirectoryPane)
				pane.get_selected_files.return_value = []
				pane.get_file_under_cursor.return_value = url
				self._assert_copy_on_pane(
					command_class, pane,
					url.rsplit('/', 1)[-1] if command_name == 'CopyFileName'
					else as_human_readable(url)
				)
			with self.subTest(command=command_name, case='no selection'):
				pane = Mock(spec=DirectoryPane)
				pane.get_selected_files.return_value = []
				pane.get_file_under_cursor.return_value = None
				self._assert_not_copied(command_class, pane)
			with self.subTest(command=command_name, case='two selected'):
				pane = Mock(spec=DirectoryPane)
				pane.get_selected_files.return_value = [url, url + '2']
				self._assert_not_copied(command_class, pane)

	def test_execution_rechecks_selection(self):
		for command_name in ('CopyFileName', 'CopyFilePath'):
			with self.subTest(command=command_name):
				pane = Mock(spec=DirectoryPane)
				pane.get_selected_files.side_effect = [
					['file://C:/folder/report.txt'],
					['file://C:/folder/report.txt', 'file://C:/folder/other.txt']
				]
				pane.get_file_under_cursor.return_value = None
				command_class = self._command_class(command_name)
				command = command_class(pane)
				self.assertTrue(command.is_visible())
				with patch(
					'core.commands.clipboard.clipboard.clear'
				) as clear, patch(
					'core.commands.clipboard.clipboard.set_text'
				) as set_text, patch(
					'core.commands.clipboard.show_status_message'
				) as status:
					command()
				clear.assert_not_called()
				set_text.assert_not_called()
				status.assert_not_called()

	def _assert_copy(self, url, name, command_name):
		pane = Mock(spec=DirectoryPane)
		pane.get_selected_files.return_value = [url]
		text = name if command_name == 'CopyFileName' else as_human_readable(url)
		self._assert_copy_on_pane(self._command_class(command_name), pane, text)

	def _assert_copy_on_pane(self, command_class, pane, text):
		command = command_class(pane)
		self.assertTrue(command.is_visible())
		with patch('core.commands.clipboard.clipboard.clear') as clear, \
				patch('core.commands.clipboard.clipboard.set_text') as set_text, \
				patch('core.commands.clipboard.show_status_message') as status:
			command()
		clear.assert_called_once_with()
		set_text.assert_called_once_with(text)
		status.assert_called_once_with(
			'Copied %s to the clipboard' % text, timeout_secs=3
		)
		pane.get_path.assert_not_called()

	def _assert_not_copied(self, command_class, pane):
		command = command_class(pane)
		self.assertFalse(command.is_visible())
		with patch('core.commands.clipboard.clipboard.clear') as clear, \
				patch('core.commands.clipboard.clipboard.set_text') as set_text, \
				patch('core.commands.clipboard.show_status_message') as status:
			command()
		clear.assert_not_called()
		set_text.assert_not_called()
		status.assert_not_called()

	def _command_class(self, name):
		from core import commands
		return getattr(commands, name)

class CopyPathsToClipboardSeparatorTest(TestCase):
	def test_uses_native_separators_by_default(self):
		self._assert_copied_paths(
			False, 'C:\\folder\\a.txt\nC:\\folder\\b.txt'
		)
	def test_can_copy_paths_with_forward_slashes(self):
		self._assert_copied_paths(
			True, 'C:/folder/a.txt\nC:/folder/b.txt'
		)
	def _assert_copied_paths(self, enabled, expected):
		pane = Mock(spec=DirectoryPane)
		pane.get_selected_files.return_value = [
			'file://C:/a.txt', 'file://C:/b.txt'
		]
		command = CopyPathsToClipboard(pane)
		with patch(
			'core.commands.clipboard.get_setting', return_value=enabled
		) as get_setting, patch(
			'core.commands.clipboard.as_human_readable',
			side_effect=lambda url: 'C:\\folder\\' + url.rsplit('/', 1)[-1]
		), patch(
			'core.commands.clipboard.clipboard.clear'
		), patch(
			'core.commands.clipboard.clipboard.set_text'
		) as set_text, patch(
			'core.commands.clipboard.show_status_message'
		):
			command()
		get_setting.assert_called_once_with(
			'Core Settings.json', 'copy_paths_with_forward_slashes', False
		)
		set_text.assert_called_once_with(expected)

	def test_toggle_flips_and_saves_the_setting(self):
		command = ToggleCopyPathsWithForwardSlashes(Mock())
		with patch(
			'core.commands.clipboard.get_setting', return_value=False
		) as get_setting, patch(
			'core.commands.clipboard.save_setting'
		) as save_setting, patch(
			'core.commands.clipboard.show_status_message'
		) as show_status_message:
			command()
		get_setting.assert_called_once_with(
			'Core Settings.json', 'copy_paths_with_forward_slashes', False
		)
		save_setting.assert_called_once_with(
			'Core Settings.json', 'copy_paths_with_forward_slashes', True
		)
		show_status_message.assert_called_once()

class NoSelectionTest(TestCase):
	def test_copy_alerts_when_nothing_is_chosen(self):
		with patch.object(CopyToClipboard, 'get_chosen_files', return_value=[]), \
			 patch('core.commands.clipboard.show_alert') as show_alert:
			CopyToClipboard(FakePane())()
		show_alert.assert_called_once_with(NO_SELECTION)
	def test_cut_alerts_when_nothing_is_chosen(self):
		with patch.object(Cut, 'get_chosen_files', return_value=[]), \
				patch('core.commands.clipboard.PLATFORM', 'Windows'), \
				patch('core.commands.clipboard.show_alert') as show_alert:
			Cut(FakePane())()
		show_alert.assert_called_once_with(NO_SELECTION)

class PasteVirtualFilesTest(TestCase):
	def test_pastes_virtual_files_and_shows_command(self):
		pane = Mock(spec=DirectoryPane)
		pane.get_path.return_value = 'file://C:/destination'
		data_object = object()
		files = ['file://C:/temp/attachment.pdf']
		command = Paste(pane)
		with patch('core.commands.clipboard.clipboard.get_files', return_value=[]), \
				patch('core.commands.clipboard.get_clipboard_data_object',
					return_value=data_object), \
				patch('core.commands.clipboard.has_virtual_files', return_value=True), \
				patch('core.commands.clipboard.save_virtual_files',
					return_value=files), \
				patch('core.commands.clipboard.clipboard.files_were_cut',
					return_value=True) as files_were_cut:
			self.assertTrue(command.is_visible())
			command()
		files_were_cut.assert_not_called()
		pane.run_command.assert_called_once_with('copy', {
			'files': files, 'dest_dir': 'file://C:/destination'
		})

	def test_hides_paste_without_files_or_virtual_clipboard(self):
		pane = Mock(spec=DirectoryPane)
		with patch('core.commands.clipboard.clipboard.get_files', return_value=[]), \
				patch('core.commands.clipboard.get_clipboard_data_object',
					return_value=None):
			self.assertFalse(Paste(pane).is_visible())

class ReportClipboardActionTest(TestCase):

	"""
	The status message names the first file and counts the rest, so its
	plural has to follow the *remainder*, not the total: two files leave one
	other, which is singular.
	"""

	def test_one_file(self):
		self.assertEqual('Copying %s' % self._path('a'), self._report(['a']))
	def test_two_files_says_one_other_singular(self):
		self.assertEqual(
			'Copying %s and 1 other file' % self._path('a'),
			self._report(['a', 'b'])
		)
	def test_three_files_says_two_others_plural(self):
		self.assertEqual(
			'Copying %s and 2 other files' % self._path('a'),
			self._report(['a', 'b', 'c'])
		)
	def test_suffix_and_type_are_applied(self):
		self.assertEqual(
			'Copied %s and 1 other path to the clipboard' % self._path('a'),
			self._report(['a', 'b'], 'Copied', ' to the clipboard', 'path')
		)
	def _report(self, names, verb='Copying', suffix='', ftype='file'):
		urls = [self._url(name) for name in names]
		with patch(
			'core.commands.clipboard.show_status_message'
		) as show_status_message:
			_report_clipboard_action(verb, urls, suffix, ftype)
		(message,), _kwargs = show_status_message.call_args
		return message
	def _url(self, name):
		return as_url('/dir/' + name)
	def _path(self, name):
		return as_human_readable(self._url(name))
