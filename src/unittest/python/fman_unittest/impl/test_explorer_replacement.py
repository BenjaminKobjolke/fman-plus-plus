import sys
import unittest
from unittest.mock import Mock, patch

if sys.platform != 'win32':
	raise unittest.SkipTest('Explorer replacement is only available on Windows')

from fman.impl import explorer_replacement as replacement


class _RegistryKey:
	def __init__(self, registry, path):
		self.registry = registry
		self.path = path
	def __enter__(self):
		return self
	def __exit__(self, *args):
		pass


class _Registry:
	def __init__(self):
		self.keys = {r'Software\Classes': {}}
		self.HKEY_CURRENT_USER = replacement.winreg.HKEY_CURRENT_USER
		self.KEY_READ = replacement.winreg.KEY_READ
		self.KEY_SET_VALUE = replacement.winreg.KEY_SET_VALUE
		self.KEY_WRITE = replacement.winreg.KEY_WRITE
		self.REG_SZ = replacement.winreg.REG_SZ

	def _path(self, root, path):
		return path if root == self.HKEY_CURRENT_USER else root.path + '\\' + path

	def OpenKey(self, root, path, reserved=0, access=0):
		full_path = self._path(root, path)
		if full_path not in self.keys:
			raise FileNotFoundError(full_path)
		return _RegistryKey(self, full_path)

	def CreateKey(self, root, path):
		full_path = self._path(root, path)
		parts = full_path.split('\\')
		for index in range(1, len(parts) + 1):
			self.keys.setdefault('\\'.join(parts[:index]), {})
		return _RegistryKey(self, full_path)

	def SetValueEx(self, key, name, reserved, value_type, value):
		key.registry.keys[key.path][name] = (value_type, value)

	def QueryValueEx(self, key, name):
		value_type, value = key.registry.keys[key.path][name]
		return value, value_type

	def DeleteValue(self, key, name):
		try:
			del key.registry.keys[key.path][name]
		except KeyError:
			raise FileNotFoundError(name)

	def EnumKey(self, key, index):
		prefix = key.path + '\\'
		children = sorted({
			path[len(prefix):].split('\\', 1)[0]
			for path in self.keys
			if path.startswith(prefix) and path != key.path
		})
		try:
			return children[index]
		except IndexError:
			raise OSError('no more registry keys')

	def DeleteKey(self, root, path):
		full_path = self._path(root, path)
		if any(key.startswith(full_path + '\\') for key in self.keys):
			raise OSError('registry key has subkeys')
		self.keys.pop(full_path, None)


class _Settings(dict):
	def __init__(self, *args):
		super().__init__(*args)
		self.flush = Mock()


class ExplorerReplacementTest(unittest.TestCase):
	def setUp(self):
		self.registry = _Registry()
		self.patches = []
		for name in ('OpenKey', 'CreateKey', 'SetValueEx', 'QueryValueEx',
					 'DeleteValue', 'EnumKey', 'DeleteKey'):
			patcher = patch.object(replacement.winreg, name,
								   getattr(self.registry, name))
			patcher.start()
			self.patches.append(patcher)
		self.addCleanup(self._stop_patches)
		self.registry.keys[r'Software\Classes\Directory'] = {}
		self.registry.keys[r'Software\Classes\Drive'] = {}
		self.registry.keys[r'Software\Classes\CLSID'] = {}
		with patch.object(replacement, '_notify_association_change'):
			replacement.disable()

	def _stop_patches(self):
		for patcher in reversed(self.patches):
			patcher.stop()

	def test_enable_writes_folder_drive_win_e_and_this_pc_commands(self):
		with patch.object(replacement.sys, 'executable',
				r'C:\Program Files\fman\fman.exe'), \
				patch.object(replacement, '_notify_association_change'):
			replacement.enable()
		classes = self.registry.keys
		for root in ('Directory', 'Drive'):
			base = 'Software\\Classes\\' + root + '\\shell'
			self.assertEqual((self.registry.REG_SZ, replacement.VERB),
				classes[base][''])
			self.assertEqual((self.registry.REG_SZ, 'Open in fman'),
				classes[base + r'\fman'][''])
			self.assertEqual((self.registry.REG_SZ,
				'"C:\\Program Files\\fman\\fman.exe" "%1"'),
				classes[base + r'\fman\command'][''])
		for clsid, suffix in ((replacement.WIN_E_CLSID, ''),
							   (replacement.THIS_PC_CLSID, ' drives://')):
			command = (
				'Software\\Classes\\CLSID\\' + clsid + '\\shell\\' +
				('opennewwindow' if not suffix else 'open') + '\\command')
			self.assertEqual((self.registry.REG_SZ,
				'"C:\\Program Files\\fman\\fman.exe"' + suffix),
				classes[command][''])
			self.assertEqual((self.registry.REG_SZ, ''),
				classes[command]['DelegateExecute'])

	def test_disable_removes_fman_keys_and_preserves_other_handlers(self):
		with patch.object(replacement.sys, 'executable', r'C:\fman\fman.exe'), \
				patch.object(replacement, '_notify_association_change'):
			replacement.enable()
		directory_shell = r'Software\Classes\Directory\shell'
		drive_shell = r'Software\Classes\Drive\shell'
		self.registry.keys[directory_shell][''] = (self.registry.REG_SZ, 'other')
		self.registry.keys[drive_shell][''] = (
			self.registry.REG_SZ, replacement.VERB)
		other = 'Software\\Classes\\CLSID\\' + replacement.WIN_E_CLSID
		self.registry.keys[other + r'\shell\opennewwindow\command'][''] = (
			self.registry.REG_SZ, '"C:\\Other\\other.exe"')
		with patch.object(replacement, '_notify_association_change'):
			replacement.disable()
		self.assertEqual((self.registry.REG_SZ, 'other'),
			self.registry.keys[r'Software\Classes\Directory\shell'][''])
		self.assertNotIn('', self.registry.keys[r'Software\Classes\Drive\shell'])
		self.assertIn(other, self.registry.keys)
		self.assertEqual('"C:\\Other\\other.exe"',
			self.registry.keys[other + r'\shell\opennewwindow\command'][''][1])
		self.assertNotIn(
			'Software\\Classes\\CLSID\\' + replacement.THIS_PC_CLSID,
			self.registry.keys,
		)
		self.assertFalse(any(r'\fman' in path for path in self.registry.keys))

	def test_is_owned_checks_verbs_and_clsids_but_ignores_exe_directory(self):
		with patch.object(replacement.sys, 'executable', r'C:\fman\fman.exe'), \
				patch.object(replacement, '_notify_association_change'):
			replacement.enable()
		self.assertTrue(replacement.is_owned())
		directory_shell = r'Software\Classes\Directory\shell'
		self.registry.keys[directory_shell][''] = (self.registry.REG_SZ, 'other')
		self.assertFalse(replacement.is_owned())
		self.registry.keys[directory_shell][''] = (
			self.registry.REG_SZ, replacement.VERB)
		window_command = (
			'Software\\Classes\\CLSID\\' + replacement.WIN_E_CLSID +
			'\\shell\\opennewwindow\\command')
		self.registry.keys[window_command][''] = (
			self.registry.REG_SZ, '"C:\\Other\\other.exe"')
		self.assertFalse(replacement.is_owned())
		self.registry.keys[window_command][''] = (
			self.registry.REG_SZ, '"D:\\new\\fman.exe"')
		self.registry.keys['Software\\Classes\\CLSID\\' + replacement.THIS_PC_CLSID +
			'\\shell\\open\\command'][''] = (self.registry.REG_SZ,
			'"D:\\new\\fman.exe" drives://')
		self.assertTrue(replacement.is_owned())

	def test_apply_respects_support_and_setting_and_disables_after_takeover(self):
		settings = _Settings({replacement.SETTING: True})
		with patch.object(replacement.autostart, 'is_supported', return_value=False), \
				patch.object(replacement, 'enable') as enable:
			self.assertIsNone(replacement.apply(settings))
			enable.assert_not_called()
		with patch.object(replacement.autostart, 'is_supported', return_value=True):
			self.assertIsNone(replacement.apply(_Settings()))
		with patch.object(replacement.autostart, 'is_supported', return_value=True), \
				patch.object(replacement, 'is_owned', return_value=True), \
				patch.object(replacement, 'enable') as enable:
			self.assertIsNone(replacement.apply(settings))
			enable.assert_called_once_with()
		with patch.object(replacement.autostart, 'is_supported', return_value=True), \
				patch.object(replacement, 'is_owned', return_value=False), \
				patch.object(replacement, 'disable') as disable:
			self.assertEqual(replacement.STATUS_TAKEN_OVER, replacement.apply(settings))
			disable.assert_called_once_with()
		self.assertNotIn(replacement.SETTING, settings)
		settings.flush.assert_called_once_with()

	def test_toggle_persists_only_after_registry_changes_succeed(self):
		settings = _Settings()
		with patch.object(replacement.autostart, 'is_supported', return_value=False):
			self.assertEqual(replacement.STATUS_UNSUPPORTED,
				replacement.toggle(settings))
		self.assertFalse(settings)
		with patch.object(replacement.autostart, 'is_supported', return_value=True), \
				patch.object(replacement, 'enable') as enable:
			self.assertEqual(replacement.STATUS_ON, replacement.toggle(settings))
			enable.assert_called_once_with()
		self.assertTrue(settings[replacement.SETTING])
		self.assertEqual(1, settings.flush.call_count)
		with patch.object(replacement.autostart, 'is_supported', return_value=True), \
				patch.object(replacement, 'disable') as disable:
			self.assertEqual(replacement.STATUS_OFF, replacement.toggle(settings))
			disable.assert_called_once_with()
		self.assertNotIn(replacement.SETTING, settings)
		with patch.object(replacement.autostart, 'is_supported', return_value=True), \
				patch.object(replacement, 'enable', side_effect=OSError('denied')):
			self.assertIn('denied', replacement.toggle(settings))
		self.assertNotIn(replacement.SETTING, settings)
		self.assertEqual(2, settings.flush.call_count)

	def test_fix_shell_arg_repairs_quoted_drive_root_only(self):
		self.assertEqual('C:\\', replacement.fix_shell_arg('C:"'))
		self.assertEqual(r'C:\folder', replacement.fix_shell_arg(r'C:\folder'))
		self.assertEqual('drives://', replacement.fix_shell_arg('drives://'))


if __name__ == '__main__':
	unittest.main()
