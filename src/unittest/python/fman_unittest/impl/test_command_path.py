import sys
import unittest
from unittest.mock import MagicMock, patch

if sys.platform != 'win32':
	raise unittest.SkipTest('The fman PATH command is only available on Windows')

from fman.impl import command_path


class CommandPathTest(unittest.TestCase):
	def setUp(self):
		self.environment_key = MagicMock()
		self.environment_key.__enter__.return_value = self.environment_key
		self.app_key = MagicMock()
		self.app_key.__enter__.return_value = self.app_key
		self.open_key = patch.object(
			command_path.winreg, 'OpenKey', return_value=self.environment_key
		)
		self.open_key_mock = self.open_key.start()
		self.addCleanup(self.open_key.stop)
		self.create_key = patch.object(
			command_path.winreg, 'CreateKeyEx', return_value=self.app_key
		)
		self.create_key_mock = self.create_key.start()
		self.addCleanup(self.create_key.stop)
		for name in ('QueryValueEx', 'SetValueEx', 'DeleteValue'):
			registry_call = patch.object(command_path.winreg, name)
			setattr(self, name, registry_call.start())
			self.addCleanup(registry_call.stop)
		self.broadcast = patch.object(command_path, '_broadcast_environment_change')
		self.broadcast_mock = self.broadcast.start()
		self.addCleanup(self.broadcast.stop)

	def test_support_requires_frozen_windows_build_and_allows_portable(self):
		with patch.object(command_path.sys, 'platform', 'win32'), \
				patch.object(command_path.sys, 'frozen', True, create=True):
			self.assertTrue(command_path.is_supported())
		with patch.object(command_path.sys, 'platform', 'win32'), \
				patch.object(command_path.sys, 'frozen', False, create=True):
			self.assertFalse(command_path.is_supported())
		with patch.object(command_path.sys, 'platform', 'linux'), \
				patch.object(command_path.sys, 'frozen', True, create=True):
			self.assertFalse(command_path.is_supported())

	def test_bin_dir_is_next_to_frozen_executable(self):
		with patch.object(command_path.sys, 'executable', r'C:\Apps\fman\fman.exe'):
			self.assertEqual(r'C:\Apps\fman\bin', command_path.bin_dir())

	def test_contains_ignores_case_trailing_slashes_and_empty_entries(self):
		self.assertTrue(command_path.contains(
			r'C:\Other;;c:\Apps\fman\bin\;', r'C:\Apps\fman\bin'
		))
		self.assertFalse(command_path.contains(
			r'C:\Apps\fman\bin-old', r'C:\Apps\fman\bin'
		))

	def test_with_entry_appends_to_existing_path(self):
		self.assertEqual(
			'one;two;C:\\fman\\bin',
			command_path.with_entry('one;two', r'C:\fman\bin'),
		)

	def test_add_keeps_existing_path_type_and_uses_expand_string_when_missing(self):
		self.QueryValueEx.return_value = ('one;two', command_path.winreg.REG_SZ)
		with (
			patch.object(command_path, 'is_supported', return_value=True),
			patch.object(
				command_path, 'portable_app_dir', return_value=r'C:\Portable\fman'
			),
			patch.object(command_path, 'bin_dir', return_value=r'C:\fman\bin'),
		):
			command_path.toggle()
		self.SetValueEx.assert_called_once_with(
			self.environment_key, 'Path', 0, command_path.winreg.REG_SZ,
			'one;two;C:\\fman\\bin',
		)
		self.SetValueEx.reset_mock()
		self.QueryValueEx.side_effect = FileNotFoundError
		with (
			patch.object(command_path, 'is_supported', return_value=True),
			patch.object(
				command_path, 'portable_app_dir', return_value=r'C:\Portable\fman'
			),
			patch.object(command_path, 'bin_dir', return_value=r'C:\fman\bin'),
		):
			command_path.toggle()
		self.SetValueEx.assert_called_once_with(
			self.environment_key, 'Path', 0, command_path.winreg.REG_EXPAND_SZ,
			r'C:\fman\bin',
		)

	def test_add_to_empty_path_writes_only_bin_directory(self):
		self.assertEqual(r'C:\fman\bin', command_path.with_entry('', r'C:\fman\bin'))

	def test_without_entry_removes_all_matches_and_keeps_order(self):
		self.assertEqual(
			r'C:\first;C:\last',
			command_path.without_entry(
				r'C:\first;C:\fman\bin\;C:\last;C:\FMAN\BIN',
				r'c:\fman\bin',
			),
		)

	def test_toggle_on_installed_copy_clears_opt_out_and_broadcasts(self):
		self.QueryValueEx.side_effect = FileNotFoundError
		with patch.object(command_path, 'is_supported', return_value=True), \
				patch.object(command_path, 'portable_app_dir', return_value=None), \
				patch.object(command_path, 'bin_dir', return_value=r'C:\fman\bin'):
			self.assertEqual(command_path.STATUS_ON, command_path.toggle())
		self.DeleteValue.assert_called_once_with(
			self.app_key, command_path.OPT_OUT_VALUE
		)
		self.broadcast_mock.assert_called_once_with()

	def test_toggle_off_installed_copy_sets_opt_out(self):
		self.QueryValueEx.return_value = (
			r'C:\fman\bin', command_path.winreg.REG_EXPAND_SZ
		)
		with patch.object(command_path, 'is_supported', return_value=True), \
				patch.object(command_path, 'portable_app_dir', return_value=None), \
				patch.object(command_path, 'bin_dir', return_value=r'C:\fman\bin'):
			self.assertEqual(command_path.STATUS_OFF, command_path.toggle())
		self.assertIn(
			(self.app_key, command_path.OPT_OUT_VALUE, 0,
			 command_path.winreg.REG_DWORD, 1),
			[call.args for call in self.SetValueEx.call_args_list],
		)
		self.broadcast_mock.assert_called_once_with()

	def test_toggle_portable_never_touches_opt_out_and_warns_before_move(self):
		self.QueryValueEx.side_effect = FileNotFoundError
		with (
			patch.object(command_path, 'is_supported', return_value=True),
			patch.object(
				command_path, 'portable_app_dir', return_value=r'C:\Portable\fman'
			),
			patch.object(command_path, 'bin_dir', return_value=r'C:\fman\bin'),
		):
			self.assertEqual(command_path.STATUS_ON_PORTABLE, command_path.toggle())
		self.create_key_mock.assert_not_called()
		self.assertFalse(any(
			call.args[1] == command_path.OPT_OUT_VALUE
			for call in self.SetValueEx.call_args_list
		))
		self.DeleteValue.assert_not_called()

	def test_unsupported_does_not_access_registry(self):
		with patch.object(command_path, 'is_supported', return_value=False):
			self.assertEqual(command_path.STATUS_UNSUPPORTED, command_path.toggle())
		self.open_key_mock.assert_not_called()
		self.create_key_mock.assert_not_called()

	def test_registry_error_is_logged_and_returned(self):
		self.open_key_mock.side_effect = OSError('registry denied')
		with patch.object(command_path, 'is_supported', return_value=True), \
				patch.object(command_path, 'portable_app_dir', return_value=None), \
				self.assertLogs(command_path.__name__, level='ERROR'):
			self.assertEqual(
				'Could not change the fman command in PATH: registry denied',
				command_path.toggle(),
			)


if __name__ == '__main__':
	unittest.main()
