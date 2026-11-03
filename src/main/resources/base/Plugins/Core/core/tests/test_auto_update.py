from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from core import auto_update


class AutoUpdateSupportTest(TestCase):
	def test_only_supported_installed_windows_build_is_supported(self):
		with patch.object(auto_update.os.path, 'isfile', return_value=True), \
				patch.multiple(
			auto_update,
			PLATFORM='Windows',
			is_frozen=Mock(return_value=True),
			portable_app_dir=Mock(return_value=None),
			get_install_mode=Mock(return_value='/CurrentUser'),
		):
			self.assertTrue(auto_update.is_supported())

		for platform, frozen, portable_dir, mode in (
			('Mac', True, None, '/CurrentUser'),
			('Windows', False, None, '/CurrentUser'),
			('Windows', True, 'portable', '/CurrentUser'),
			('Windows', True, None, None),
		):
			with self.subTest(platform=platform, frozen=frozen):
				with patch.multiple(
					auto_update,
					PLATFORM=platform,
					is_frozen=Mock(return_value=frozen),
					portable_app_dir=Mock(return_value=portable_dir),
					get_install_mode=Mock(return_value=mode),
				):
					self.assertFalse(auto_update.is_supported())

	def test_requires_uninstaller_beside_executable(self):
		with patch.multiple(
			auto_update,
			PLATFORM='Windows',
			is_frozen=Mock(return_value=True),
			portable_app_dir=Mock(return_value=None),
			get_install_mode=Mock(return_value='/CurrentUser'),
			os=Mock(),
			sys=Mock(),
		):
			auto_update.sys.executable = r'C:\Program Files\fman\fman.exe'
			auto_update.os.path.dirname.return_value = r'C:\Program Files\fman'
			auto_update.os.path.join.return_value = (
				r'C:\Program Files\fman\uninstall.exe'
			)
			auto_update.os.path.isfile.return_value = False
			self.assertFalse(auto_update.is_supported())
			auto_update.os.path.isfile.return_value = True
			self.assertTrue(auto_update.is_supported())


class InstallModeTest(TestCase):
	def setUp(self):
		self.registry = Mock()
		self.registry.HKEY_CURRENT_USER = object()
		self.registry.HKEY_LOCAL_MACHINE = object()
		self.registry.KEY_READ = 1
		self.registry.KEY_WOW64_32KEY = 2
		self.registry.OpenKey.side_effect = self._open_key
		self.registry.QueryValueEx.side_effect = self._query_value
		self.values = {}
		self._start_patch(patch.object(auto_update, 'winreg', self.registry))
		self._start_patch(patch.object(
			auto_update.sys, 'executable', r'C:\Apps\fman\fman.exe'
		))
		self._start_patch(patch.object(
			auto_update.os.path, 'isfile', return_value=True
		))
		self._start_patch(patch.object(
			auto_update.os.path, 'dirname', return_value=r'C:\Apps\fman'
		))

	def _start_patch(self, patcher):
		patcher.start()
		self.addCleanup(patcher.stop)

	def _open_key(self, hive, path, _reserved=0, access=0):
		key = (hive, path, access)
		context = MagicMock()
		context.__enter__.return_value = key
		return context

	def _query_value(self, key, _name):
		return self.values.get(key, ''), 1

	def test_detects_per_user_install(self):
		key = (
			self.registry.HKEY_CURRENT_USER,
			auto_update.REGISTRY_KEY,
			self.registry.KEY_READ,
		)
		self.values[key] = r'c:\apps\fman'
		self.assertEqual('/CurrentUser', auto_update.get_install_mode())

	def test_detects_all_users_install_in_32_bit_registry_view(self):
		key = (
			self.registry.HKEY_LOCAL_MACHINE, auto_update.REGISTRY_KEY,
			self.registry.KEY_READ | self.registry.KEY_WOW64_32KEY
		)
		self.values[key] = r'C:\Apps\fman'
		self.assertEqual('/AllUsers', auto_update.get_install_mode())
		self.registry.OpenKey.assert_any_call(
			self.registry.HKEY_LOCAL_MACHINE, auto_update.REGISTRY_KEY, 0,
			self.registry.KEY_READ | self.registry.KEY_WOW64_32KEY
		)

	def test_unknown_registry_install_is_unsupported(self):
		self.assertIsNone(auto_update.get_install_mode())

	def test_installer_command_keeps_unquoted_d_equals_last(self):
		with patch.object(auto_update, 'get_install_mode', return_value='/CurrentUser'):
			self.assertEqual(
				'"C:\\Temp\\fmanSetup.exe" /S /CurrentUser /D=C:\\Apps\\fman',
				auto_update.installer_command(r'C:\Temp\fmanSetup.exe')
			)


class AutoUpdateSettingsAndDueTest(TestCase):
	def setUp(self):
		self.setting = patch.object(auto_update, 'get_setting', return_value=None)
		self.setting.start()
		self.addCleanup(self.setting.stop)
		auto_update._last_check_time = None
		self.addCleanup(setattr, auto_update, '_last_check_time', None)

	def test_settings_use_approved_defaults_and_keys(self):
		self.assertFalse(auto_update.is_enabled())
		self.assertEqual(24, auto_update.interval_hours())
		self.assertEqual((1, 720), (
			auto_update.MIN_INTERVAL_HOURS, auto_update.MAX_INTERVAL_HOURS
		))
		self.assertEqual(30, auto_update.COUNTDOWN_SECONDS)
		self.assertEqual(600, auto_update.TIMER_SLACK_SECONDS)
		self.assertEqual(
			'Automatic updates only work with the installed Windows version.',
			auto_update.UNSUPPORTED_MESSAGE
		)
		self.setting.stop()
		with patch.object(auto_update, 'get_setting', side_effect=(True, 1)) as get:
			self.assertTrue(auto_update.is_enabled())
			self.assertEqual(1, auto_update.interval_hours())
		self.assertEqual(
			[(auto_update.SETTINGS_FILE, auto_update.AUTO_UPDATE_SETTING, False),
			 (auto_update.SETTINGS_FILE, auto_update.AUTO_UPDATE_INTERVAL_SETTING, 24)],
			[get.call_args_list[0].args, get.call_args_list[1].args]
		)

	def test_invalid_interval_falls_back_to_default(self):
		for invalid in (0, 721, '1', None):
			with self.subTest(invalid=invalid):
				with patch.object(auto_update, 'get_setting', return_value=invalid):
					self.assertEqual(24, auto_update.interval_hours())

	def test_check_interval_falls_back_to_24_hours_when_disabled_or_unsupported(self):
		with patch.object(auto_update, 'is_enabled', return_value=False), \
				patch.object(auto_update, 'is_supported', return_value=True):
			self.assertEqual(24 * 60 * 60, auto_update.check_interval_seconds())
		with patch.object(auto_update, 'is_enabled', return_value=True), \
				patch.object(auto_update, 'is_supported', return_value=False):
			self.assertEqual(24 * 60 * 60, auto_update.check_interval_seconds())

	def test_configured_interval_applies_when_enabled_and_supported(self):
		with patch.object(auto_update, 'is_enabled', return_value=True), \
				patch.object(auto_update, 'is_supported', return_value=True), \
				patch.object(auto_update, 'interval_hours', return_value=1):
			self.assertEqual(60 * 60, auto_update.check_interval_seconds())

	def test_first_check_is_due_and_later_checks_respect_interval_and_slack(self):
		with patch.object(auto_update, 'check_interval_seconds', return_value=3600):
			self.assertTrue(auto_update.is_check_due(now=100))
			self.assertFalse(auto_update.is_check_due(now=3099))
			self.assertTrue(auto_update.is_check_due(now=3100))
			self.assertFalse(auto_update.is_check_due(now=6099))
			self.assertTrue(auto_update.is_check_due(now=6100))

