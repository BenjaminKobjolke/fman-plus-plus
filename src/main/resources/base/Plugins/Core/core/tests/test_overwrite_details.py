from core import Modified
from core.overwrite_details import free_name, get_details, is_enabled
from core.tests import StubFS
from fman.impl.overwrite_dialog import FileDetails
from unittest import TestCase
from unittest.mock import MagicMock, patch

from core.overwrite_details import SETTING_KEY


class _FileSystem:
	def __init__(self, values):
		self.values = values

	def query(self, url, name):
		value = self.values[url, name]
		if isinstance(value, Exception):
			raise value
		return value


class OverwriteDetailsTest(TestCase):
	def test_details_mark_the_larger_and_newer_file(self):
		fs = _FileSystem({
			('file:///existing.txt', 'size_bytes'): 10,
			('file:///incoming.txt', 'size_bytes'): 20,
			('file:///existing.txt', 'modified_datetime'): 1,
			('file:///incoming.txt', 'modified_datetime'): 2,
		})
		with patch('core.overwrite_details.is_enabled', return_value=True), \
				patch.object(Modified, 'get_str', side_effect=['old date', 'new date']):
			details = get_details(fs, 'file:///incoming.txt', 'file:///existing.txt')

		self.assertEqual(
			(FileDetails('10 B', 'old date', is_larger=False, is_newer=False),
			 FileDetails('20 B', 'new date', is_larger=True, is_newer=True)),
			details
		)

	def test_equal_values_have_no_marks(self):
		fs = _FileSystem({
			('file:///existing.txt', 'size_bytes'): 10,
			('file:///incoming.txt', 'size_bytes'): 10,
			('file:///existing.txt', 'modified_datetime'): 2,
			('file:///incoming.txt', 'modified_datetime'): 2,
		})
		with patch('core.overwrite_details.is_enabled', return_value=True), \
				patch.object(Modified, 'get_str', return_value='same date'):
			details = get_details(fs, 'file:///incoming.txt', 'file:///existing.txt')

		self.assertFalse(details[0].is_larger or details[0].is_newer)
		self.assertFalse(details[1].is_larger or details[1].is_newer)

	def test_unreadable_or_missing_values_are_empty_and_unmarked(self):
		fs = _FileSystem({
			('file:///existing.txt', 'size_bytes'): OSError('offline'),
			('file:///incoming.txt', 'size_bytes'): None,
			('file:///existing.txt', 'modified_datetime'): OSError('offline'),
			('file:///incoming.txt', 'modified_datetime'): None,
		})
		with patch('core.overwrite_details.is_enabled', return_value=True), \
				patch.object(Modified, 'get_str', side_effect=['', '']):
			details = get_details(fs, 'file:///incoming.txt', 'file:///existing.txt')

		self.assertEqual((FileDetails('', ''), FileDetails('', '')), details)

	def test_disabled_setting_skips_all_file_queries(self):
		fs = MagicMock(spec=StubFS)
		fs.query = MagicMock()
		with patch('core.overwrite_details.is_enabled', return_value=False):
			self.assertIsNone(get_details(fs, 'file:///incoming', 'file:///existing'))
		fs.query.assert_not_called()

	def test_is_enabled_uses_the_core_default_and_key(self):
		with patch(
			'core.overwrite_details.get_setting', return_value=True
		) as get_setting:
			self.assertTrue(is_enabled())
		get_setting.assert_called_once_with('Core Settings.json', SETTING_KEY, True)

	def test_free_names_handle_hidden_and_extensionless_files(self):
		self.assertEqual(
			'file:///folder/.gitignore (2)',
			free_name('file:///folder/.gitignore', lambda _url: False),
		)
		self.assertEqual(
			'file:///folder/README (2)',
			free_name('file:///folder/README', lambda _url: False),
		)

	def test_free_name_skips_taken_numbered_names(self):
		self.assertEqual(
			'file:///folder/report (3).txt',
			free_name(
				'file:///folder/report.txt',
				lambda url: url.endswith('report (2).txt'),
			),
		)

	def test_versions_are_only_read_for_local_windows_executables(self):
		version_info = {
			'FileVersionMS': (1 << 16) + 2,
			'FileVersionLS': (3 << 16) + 4,
		}
		win32api = MagicMock()
		win32api.GetFileVersionInfo.return_value = version_info
		with patch.dict('sys.modules', {'win32api': win32api}), \
				patch('core.overwrite_details.PLATFORM', 'Windows'):
			self.assertEqual(
				'1.2.3.4',
				__import__('core.overwrite_details', fromlist=['_version'])._version(
					'file:///folder/app.EXE'
				),
			)
			self.assertEqual('', __import__(
				'core.overwrite_details', fromlist=['_version']
			)._version('file:///folder/readme.txt'))
			self.assertEqual('', __import__(
				'core.overwrite_details', fromlist=['_version']
			)._version('sftp:///folder/app.exe'))
		win32api.GetFileVersionInfo.assert_called_once_with('/folder/app.EXE', '\\')

	def test_version_read_failures_return_empty(self):
		win32api = MagicMock()
		win32api.GetFileVersionInfo.side_effect = OSError('no version resource')
		with patch.dict('sys.modules', {'win32api': win32api}), \
				patch('core.overwrite_details.PLATFORM', 'Windows'):
			version = __import__(
				'core.overwrite_details', fromlist=['_version']
			)._version('file:///folder/app.dll')
		self.assertEqual('', version)


class ToggleOverwriteDetailsTest(TestCase):
	def test_toggle_saves_the_new_value_and_reports_it(self):
		from core.commands.overwrite_details import ToggleOverwriteDetails

		with patch('core.commands.overwrite_details.is_enabled', return_value=True), \
				patch('core.commands.overwrite_details.save_setting') as save_setting, \
				patch('core.commands.overwrite_details.show_status_message') as status:
			ToggleOverwriteDetails(None)()

		save_setting.assert_called_once_with('Core Settings.json', SETTING_KEY, False)
		status.assert_called_once_with('Overwrite details: off', timeout_secs=3)
		self.assertEqual(('Toggle overwrite details',), ToggleOverwriteDetails.aliases)
