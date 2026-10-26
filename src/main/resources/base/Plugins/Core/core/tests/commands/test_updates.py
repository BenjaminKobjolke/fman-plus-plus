import os
import tempfile
from core.commands.updates import CheckForUpdates
from core.updates import UpdateStatus
from fman import NO, YES, links
from subprocess import DEVNULL
from unittest import TestCase
from unittest.mock import patch
from urllib.error import URLError


class CheckForUpdatesTest(TestCase):
	def setUp(self):
		self.patches = {}
		for name in (
			'check_for_update', 'show_alert', 'load_json', 'save_json',
			'QDesktopServices', 'show_status_message', 'clear_status_message',
			'submit_task', 'Popen', 'sys', 'PLATFORM', 'net.download',
		):
			p = patch('core.commands.updates.' + name, 'Linux') \
				if name == 'PLATFORM' else patch('core.commands.updates.' + name)
			self.patches[name] = p.start()
			self.addCleanup(p.stop)
		self.patches['load_json'].return_value = {}
		self.patches['check_for_update'].return_value = UpdateStatus(
			'1.7.13', '1.8.0'
		)

	def test_alias(self):
		self.assertEqual(('Check for updates',), CheckForUpdates.aliases)

	def test_manual_yes_on_linux_opens_release_page(self):
		self.patches['show_alert'].return_value = YES
		CheckForUpdates(None)()
		url = self.patches['QDesktopServices'].openUrl.call_args.args[0]
		self.assertEqual(links.RELEASES, url.toString())
		self.patches['clear_status_message'].assert_called_once()

	def test_manual_yes_on_windows_downloads_and_runs_installer(self):
		self._download_update('Windows', self._write_download)
		url = self.patches['net.download'].call_args.args[0]
		path = self.patches['net.download'].call_args.args[1]
		self.assertEqual(
			'https://github.com/%s/releases/download/1.8.0/fmanSetup.exe'
			% links.GITHUB_REPO,
			url
		)
		self.assertEqual('fmanSetup.exe', os.path.basename(path))
		self.patches['Popen'].assert_called_once_with(
			[path], cwd=os.path.dirname(path), stdout=DEVNULL, stderr=DEVNULL
		)
		self.patches['sys'].exit.assert_called_once_with(0)

	def test_manual_yes_on_mac_opens_downloaded_dmg(self):
		self._download_update('Mac', self._write_download)
		path = self.patches['net.download'].call_args.args[1]
		self.assertEqual('fman.dmg', os.path.basename(path))
		self.patches['Popen'].assert_called_once_with(['open', path])
		self.patches['sys'].exit.assert_not_called()

	def test_download_error_reports_and_opens_release_page(self):
		self._download_update('Windows', self._fail_download)
		self.assertTrue(any(
			'Could not download the update' in call.args[0]
			for call in self.patches['show_alert'].call_args_list[1:]
		))
		url = self.patches['QDesktopServices'].openUrl.call_args.args[0]
		self.assertEqual(links.RELEASES, url.toString())
		self.patches['Popen'].assert_not_called()

	def test_canceled_download_has_no_follow_up(self):
		self._download_update('Windows', lambda _url, _path, _task: None)
		self.patches['Popen'].assert_not_called()
		self.patches['sys'].exit.assert_not_called()
		self.assertEqual(1, self.patches['show_alert'].call_count)

	def _download_update(self, platform, download):
		self.patches['show_alert'].return_value = YES
		self.patches['submit_task'].side_effect = lambda task: task()
		self.patches['net.download'].side_effect = download
		with tempfile.TemporaryDirectory() as directory:
			with patch(
				'core.commands.updates.tempfile.gettempdir', return_value=directory
			):
				with patch('core.commands.updates.PLATFORM', platform):
					CheckForUpdates(None)()

	@staticmethod
	def _write_download(_url, path, _task):
		with open(path, 'wb') as downloaded:
			downloaded.write(b'installer')

	@staticmethod
	def _fail_download(*_args):
		raise URLError('offline')

	def test_manual_no_does_not_open_page(self):
		self.patches['show_alert'].return_value = NO
		CheckForUpdates(None)()
		self.patches['QDesktopServices'].openUrl.assert_not_called()

	def test_manual_up_to_date_reports_result(self):
		self.patches['check_for_update'].return_value = UpdateStatus(
			'1.8.0', '1.8.0'
		)
		CheckForUpdates(None)()
		self.patches['show_alert'].assert_called_once_with(
			'fman++ 1.8.0 is up to date.'
		)

	def test_manual_failures_report_error(self):
		for error in (URLError('offline'), ValueError('bad tag'), KeyError('tag')):
			with self.subTest(error=error):
				self.patches['show_alert'].reset_mock()
				self.patches['check_for_update'].side_effect = error
				CheckForUpdates(None)()
				self.assertIn(
					'Could not check for updates',
					self.patches['show_alert'].call_args.args[0]
				)

	def test_silent_no_update_or_error_is_quiet(self):
		self.patches['check_for_update'].return_value = UpdateStatus(
			'1.8.0', '1.8.0'
		)
		CheckForUpdates(None)(silent=True)
		self.patches['check_for_update'].side_effect = URLError('offline')
		CheckForUpdates(None)(silent=True)
		self.patches['show_alert'].assert_not_called()

	def test_silent_new_update_announces_once(self):
		CheckForUpdates(None)(silent=True)
		self.patches['show_alert'].assert_called_once()
		self.patches['save_json'].assert_called_once_with('Update Check.json')
		self.assertEqual(
			'1.8.0', self.patches['load_json'].return_value['announced']
		)
		self.patches['show_alert'].reset_mock()
		CheckForUpdates(None)(silent=True)
		self.patches['show_alert'].assert_not_called()

	def test_manual_ignores_prior_announcement(self):
		self.patches['load_json'].return_value = {'announced': '1.8.0'}
		CheckForUpdates(None)()
		self.patches['show_alert'].assert_called_once()
