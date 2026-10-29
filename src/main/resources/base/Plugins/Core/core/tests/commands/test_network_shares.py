from core.commands import network_shares as commands
from core.fs.local.windows import shares
from core.tests.commands import FakePane
from fman import PLATFORM
from unittest import TestCase, skipIf
from unittest.mock import patch


@skipIf(PLATFORM != 'Windows', 'network shares only exist on Windows')
class ConnectNetworkShareTest(TestCase):
	def test_drive_letter_validation_accepts_z_and_z_colon(self):
		for value in ('z', 'Z:'):
			with self.subTest(value=value):
				self._connect(value)
				self.assertEqual('Z', self.connect.call_args.args[1])

	def test_empty_drive_letter_connects_without_mapping(self):
		self._connect('')
		self.assertIsNone(self.connect.call_args.args[1])

	def test_invalid_drive_letter_is_rejected(self):
		self._connect('ZZ')
		self.connect.assert_not_called()
		self.alert.assert_called_once()

	def test_in_use_drive_letter_is_rejected(self):
		self._connect('Z', in_use=True)
		self.connect.assert_not_called()
		self.assertIn('Z:', self.alert.call_args.args[0])

	def _connect(self, letter, in_use=False):
		self.pane = FakePane(url='file:///C:/')
		self.pane.get_path = lambda: self.pane._url
		self.connect = self._patch('connect_share', return_value=True)
		self.alert = self._patch('show_alert')
		self._patch('_drive_letter_in_use', return_value=in_use)
		with patch.object(
				commands, 'show_prompt',
				side_effect=[('smb://server/share', True), (letter, True)]
		), patch.object(
				commands.win32gui, 'GetForegroundWindow', return_value=17
		):
			commands.ConnectNetworkShare(self.pane)()
	def _patch(self, name, **kwargs):
		patcher = patch('core.commands.network_shares.' + name, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()


@skipIf(PLATFORM != 'Windows', 'network shares only exist on Windows')
class ShareLoginTest(TestCase):
	def test_local_path_does_not_call_windows(self):
		with patch.object(commands, 'connect_share') as connect:
			self.assertEqual(commands.ShareLogin.NOT_A_SHARE, commands.log_in_to_share('file:///C:/folder'))
		connect.assert_not_called()

	def test_successful_login(self):
		with patch.object(commands, 'connect_share', return_value=True) as connect, \
				patch.object(commands.win32gui, 'GetForegroundWindow', return_value=17):
			result = commands.log_in_to_share('file:////server/share/folder')
		self.assertEqual(commands.ShareLogin.CONNECTED, result)
		connect.assert_called_once_with(r'\\server\share', owner_hwnd=17)

	def test_cancelled_login_is_silent(self):
		with patch.object(commands, 'connect_share', return_value=False), \
				patch.object(commands, 'show_alert') as alert, \
				patch.object(commands.win32gui, 'GetForegroundWindow', return_value=17):
			self.assertEqual(commands.ShareLogin.CANCELLED, commands.log_in_to_share('file:////server/share'))
		alert.assert_not_called()

	def test_failed_login_alerts(self):
		error = shares.WNetError(5, 'connect', 'denied')
		with patch.object(commands, 'connect_share', side_effect=error), \
				patch.object(commands, 'show_alert') as alert, \
				patch.object(commands.win32gui, 'GetForegroundWindow', return_value=17):
			self.assertEqual(commands.ShareLogin.FAILED, commands.log_in_to_share('file:////server/share'))
		alert.assert_called_once()
