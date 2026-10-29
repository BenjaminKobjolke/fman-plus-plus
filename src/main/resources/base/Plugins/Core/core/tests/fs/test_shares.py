from core.fs.local.windows import shares
from fman import PLATFORM
from unittest import TestCase, skipIf
from unittest.mock import Mock, patch

_MODULE = 'core.fs.local.windows.shares'


@skipIf(PLATFORM != 'Windows', 'network shares only exist on Windows')
class ShareAddressTest(TestCase):
	def test_parse_smb_share_and_subpath(self):
		address = shares.parse_share_address(' smb://10.0.0.20/share/sub/dir/ ')
		self.assertEqual(r'\\10.0.0.20\share', address.share_unc)
		self.assertEqual(r'file:////10.0.0.20/share/sub/dir', address.as_fman_url())

	def test_parse_server_only(self):
		address = shares.parse_share_address('smb://10.0.0.20')
		self.assertEqual('network://10.0.0.20', address.as_fman_url())

	def test_parse_unc_and_forward_slash_addresses(self):
		unc_address = shares.parse_share_address('\\\\server\\share\\')
		forward_slash_address = shares.parse_share_address('//server/share')
		self.assertEqual(r'\\server\share', unc_address.share_unc)
		self.assertEqual(r'\\server\share', forward_slash_address.share_unc)

	def test_reject_non_share_paths(self):
		for path in (r'C:\x', 'file://server/share', 'smb://'):
			self.assertIsNone(shares.parse_share_address(path))


@skipIf(PLATFORM != 'Windows', 'network shares only exist on Windows')
class ShareConnectionTest(TestCase):
	def test_connect_without_drive_letter_uses_interactive_credentials(self):
		resource = Mock()
		with patch(_MODULE + '.NETRESOURCE', return_value=resource), \
				patch(_MODULE + '.WNetAddConnection3') as connect:
			self.assertTrue(shares.connect_share(r'\\server\share', owner_hwnd=7))
		self.assertEqual(r'\\server\share', resource.lpRemoteName)
		self.assertIsNone(resource.lpLocalName)
		self.assertEqual(shares.CONNECT_INTERACTIVE, connect.call_args.args[4])
		self.assertEqual(7, connect.call_args.args[0])

	def test_connect_with_letter_persists_connection(self):
		resource = Mock()
		with patch(_MODULE + '.NETRESOURCE', return_value=resource), \
				patch(_MODULE + '.WNetAddConnection3') as connect:
			self.assertTrue(shares.connect_share(r'\\server\share', 'Z'))
		self.assertEqual('Z:', resource.lpLocalName)
		self.assertEqual(
			shares.CONNECT_INTERACTIVE | shares.CONNECT_UPDATE_PROFILE,
			connect.call_args.args[4]
		)

	def test_cancelled_connect_returns_false(self):
		cancelled = shares.WNetError(
			shares.ERROR_CANCELLED, 'connect', 'cancelled'
		)
		with patch(_MODULE + '.WNetAddConnection3', side_effect=cancelled):
			self.assertFalse(shares.connect_share(r'\\server\share'))

	def test_other_connect_errors_propagate(self):
		error = shares.WNetError(5, 'connect', 'denied')
		with patch(_MODULE + '.WNetAddConnection3', side_effect=error):
			with self.assertRaises(shares.WNetError):
				shares.connect_share(r'\\server\share')

	def test_list_connections_maps_resources_and_closes_enum(self):
		resources = [Mock(lpLocalName='Z:', lpRemoteName=r'\\server\mapped'),
			Mock(lpLocalName=None, lpRemoteName=r'\\server\plain')]
		enum = Mock()
		with patch(_MODULE + '.WNetOpenEnum', return_value=enum), \
				patch(_MODULE + '.WNetEnumResource', return_value=resources):
			connections = shares.list_connections()
		enum.Close.assert_called_once_with()
		self.assertEqual(
			('Z:', r'\\server\mapped'),
			(connections[0].local_name, connections[0].remote_name)
		)
		self.assertEqual(
			('', r'\\server\plain'),
			(connections[1].local_name, connections[1].remote_name)
		)

	def test_disconnect_uses_profile_only_for_mapped_drive_and_never_forces(self):
		with patch(_MODULE + '.WNetCancelConnection2') as disconnect:
			shares.disconnect(shares.ShareConnection('Z:', r'\\server\mapped'))
			disconnect.assert_called_once_with(
				'Z:', shares.CONNECT_UPDATE_PROFILE, False
			)
		with patch(_MODULE + '.WNetCancelConnection2') as disconnect:
			shares.disconnect(shares.ShareConnection('', r'\\server\plain'))
			disconnect.assert_called_once_with(
				r'\\server\plain', 0, False
			)

	def test_open_files_error_explains_how_to_disconnect(self):
		error = shares.WNetError(
			shares.ERROR_OPEN_FILES, 'disconnect', 'The network resource is in use.'
		)
		self.assertIn('Files on it are still open.', shares.describe_wnet_error(error))
