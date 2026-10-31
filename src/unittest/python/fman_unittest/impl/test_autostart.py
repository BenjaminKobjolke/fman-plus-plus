import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

if sys.platform != 'win32':
	raise unittest.SkipTest('Windows sign-in startup is only available on Windows')

from fman.impl import autostart


class _Settings(dict):
	def __init__(self, *args):
		super().__init__(*args)
		self.flush = Mock()


class AutostartTest(unittest.TestCase):
	def setUp(self):
		self.registry_key = MagicMock()
		self.registry_key.__enter__.return_value = self.registry_key
		self.open_key = patch.object(
			autostart.winreg, 'OpenKey', return_value=self.registry_key
		)
		self.open_key_mock = self.open_key.start()
		self.addCleanup(self.open_key.stop)
		for name in ('SetValueEx', 'DeleteValue'):
			registry_call = patch.object(autostart.winreg, name)
			setattr(self, name, registry_call.start())
			self.addCleanup(registry_call.stop)

	def test_run_command_quotes_executable_and_appends_tray_argument(self):
		with patch.object(
			autostart.sys, 'executable', r'C:\Program Files\fman\fman.exe'
		):
			self.assertEqual(
				'"C:\\Program Files\\fman\\fman.exe" --tray',
				autostart.run_command(),
			)

	def test_support_requires_installed_frozen_windows_build(self):
		with patch.object(autostart.sys, 'platform', 'win32'), \
				patch.object(autostart.sys, 'frozen', True, create=True), \
				patch.object(autostart, 'portable_app_dir', return_value=None):
			self.assertTrue(autostart.is_supported())
		with patch.object(autostart.sys, 'platform', 'win32'), \
				patch.object(autostart.sys, 'frozen', False, create=True):
			self.assertFalse(autostart.is_supported())
		with patch.object(autostart.sys, 'platform', 'linux'), \
				patch.object(autostart.sys, 'frozen', True, create=True):
			self.assertFalse(autostart.is_supported())
		with patch.object(autostart.sys, 'platform', 'win32'), \
				patch.object(autostart.sys, 'frozen', True, create=True), \
				patch.object(autostart, 'portable_app_dir', return_value=r'C:\fman'):
			self.assertFalse(autostart.is_supported())

	def test_enable_writes_quoted_tray_command_to_current_user_run_key(self):
		with patch.object(autostart, 'is_supported', return_value=True), \
				patch.object(
					autostart, 'run_command', return_value='"fman.exe" --tray'
				):
			autostart.enable()
		self.open_key_mock.assert_called_once_with(
			autostart.winreg.HKEY_CURRENT_USER,
			autostart.RUN_KEY,
			0,
			autostart.winreg.KEY_SET_VALUE,
		)
		self.SetValueEx.assert_called_once_with(
			self.registry_key,
			autostart.RUN_VALUE,
			0,
			autostart.winreg.REG_SZ,
			'"fman.exe" --tray',
		)

	def test_disable_removes_run_value_and_ignores_only_missing_value(self):
		autostart.disable()
		self.DeleteValue.assert_called_once_with(
			self.registry_key, autostart.RUN_VALUE
		)
		self.DeleteValue.side_effect = FileNotFoundError
		autostart.disable()
		self.DeleteValue.side_effect = OSError('registry unavailable')
		with self.assertRaises(OSError):
			autostart.disable()

	def test_toggle_enables_registry_before_persisting_setting(self):
		settings = _Settings()
		with patch.object(autostart, 'is_supported', return_value=True), \
				patch.object(autostart, 'enable') as enable:
			self.assertEqual('fman will start with Windows', autostart.toggle(settings))
		enable.assert_called_once_with()
		self.assertIs(settings[autostart.SETTING], True)
		settings.flush.assert_called_once_with()

	def test_toggle_disables_registry_before_removing_setting(self):
		settings = _Settings({autostart.SETTING: True})
		with patch.object(autostart, 'is_supported', return_value=True), \
				patch.object(autostart, 'disable') as disable:
			self.assertEqual(
				'fman will not start with Windows', autostart.toggle(settings)
			)
		disable.assert_called_once_with()
		self.assertNotIn(autostart.SETTING, settings)
		settings.flush.assert_called_once_with()

	def test_toggle_on_unsupported_build_does_not_change_settings(self):
		settings = _Settings()
		with patch.object(autostart, 'is_supported', return_value=False):
			message = autostart.toggle(settings)
		self.assertIn('installed fman', message)
		self.assertEqual({}, settings)
		settings.flush.assert_not_called()

	def test_toggle_registry_error_leaves_settings_unchanged_and_logs(self):
		settings = _Settings()
		with patch.object(autostart, 'is_supported', return_value=True), \
				patch.object(
					autostart, 'enable', side_effect=OSError('registry denied')
				), \
				self.assertLogs(autostart.__name__, level='ERROR'):
			self.assertEqual(
				'Could not change start with Windows: registry denied',
				autostart.toggle(settings),
			)
		self.assertEqual({}, settings)
		settings.flush.assert_not_called()

	def test_apply_refreshes_enabled_entry_only_for_supported_build(self):
		settings = _Settings({autostart.SETTING: True})
		with patch.object(autostart, 'is_supported', return_value=True), \
				patch.object(autostart, 'enable') as enable:
			autostart.apply(settings)
		enable.assert_called_once_with()
		with patch.object(autostart, 'is_supported', return_value=False), \
				patch.object(autostart, 'enable') as enable:
			autostart.apply(settings)
		enable.assert_not_called()
		with patch.object(autostart, 'is_supported', return_value=True), \
				patch.object(autostart, 'enable') as enable:
			autostart.apply(_Settings())
		enable.assert_not_called()


if __name__ == '__main__':
	unittest.main()
