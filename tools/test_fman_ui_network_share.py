from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
from network_share import (
	loopback_unc, make_network_share, network_url,
)


class NetworkShareTest(TestCase):
	def test_loopback_unc_requires_a_drive_and_uses_the_admin_share(self):
		self.assertEqual(
			r'\\localhost\D$\t\fman-ui\abc\share',
			loopback_unc(Path(r'D:\t\fman-ui\abc\share')))
		with self.assertRaises(ValueError):
			loopback_unc(Path(r'\\server\x\share'))

	def test_network_url_maps_the_unc_to_the_network_filesystem(self):
		self.assertEqual(
			'network://localhost/D$/t/fman-ui/abc/share',
			network_url(r'\\localhost\D$\t\fman-ui\abc\share'))

	def test_make_network_share_creates_fixture_and_returns_paths(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			with patch('network_share.loopback_unc',
					return_value=r'\\localhost\D$\share'), \
				patch('network_share.Path.is_dir', return_value=True):
				fixture = make_network_share(root, 1000)
			self.assertEqual(root / 'share', fixture.path)
			self.assertEqual(r'\\localhost\D$\share', fixture.unc)
			self.assertEqual('network://localhost/D$/share', fixture.url)
			self.assertTrue((fixture.path / 'visible.txt').is_file())
			self.assertTrue((fixture.path / 'folder').is_dir())

	def test_make_network_share_reports_an_unreachable_unc(self):
		with TemporaryDirectory() as temp, \
			patch('network_share.loopback_unc', return_value=r'\\localhost\D$\share'), \
			patch('network_share.Path.is_dir', return_value=False):
			with self.assertRaisesRegex(RuntimeError, r'\\\\localhost\\D\$\\share'):
				make_network_share(Path(temp) / 'session', 1000)


if __name__ == '__main__':
	from unittest import main
	main()
