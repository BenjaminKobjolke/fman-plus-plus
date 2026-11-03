from unittest import TestCase
from unittest.mock import patch

from core.commands.folder_refresh import (
	FTP, LOCAL, NETWORK, _category_of, _get_refresh_seconds, _is_enabled, _toggle
)


class CategoryOfTest(TestCase):
	def test_classifies_local_network_and_ftp_locations(self):
		self.assertIs(LOCAL, _category_of('file://C:/x'))
		self.assertIs(NETWORK, _category_of('file:////server/share'))
		self.assertIs(NETWORK, _category_of('network://'))
		for url in (
			'ftp://host/path', 'ftps://host/path', 'sftp://host/path'
		):
			with self.subTest(url=url):
				self.assertIs(FTP, _category_of(url))

	def test_classifies_mapped_drives_as_network_only_on_windows(self):
		with (
			patch('core.commands.folder_refresh.PLATFORM', 'Windows'),
			patch('core.commands.folder_refresh._is_remote', return_value=True)
		):
			self.assertIs(NETWORK, _category_of('file://Z:/x'))
		with (
			patch('core.commands.folder_refresh.PLATFORM', 'Linux'),
			patch(
				'core.commands.folder_refresh._is_remote', return_value=True
			) as is_remote
		):
			self.assertIs(LOCAL, _category_of('file://Z:/x'))
			is_remote.assert_not_called()

	def test_ignores_non_refreshable_schemes(self):
		self.assertIsNone(_category_of('drives://'))
		self.assertIsNone(_category_of('zip://archive.zip'))


class RefreshSettingsTest(TestCase):
	def test_absent_interval_uses_five_seconds(self):
		with patch('core.commands.folder_refresh.get_setting', return_value=5):
			self.assertEqual(5, _get_refresh_seconds(LOCAL))

	def test_valid_interval_is_used(self):
		with patch('core.commands.folder_refresh.get_setting', return_value=30):
			self.assertEqual(30, _get_refresh_seconds(NETWORK))

	def test_invalid_intervals_use_five_seconds(self):
		for value in (0, -1, '5', True, None):
			with (
				self.subTest(value=value),
				patch(
					'core.commands.folder_refresh.get_setting', return_value=value
				)
			):
				self.assertEqual(5, _get_refresh_seconds(FTP))

	def test_only_true_enables_refresh(self):
		for value, expected in (
			(None, False), (False, False), (1, False), (True, True)
		):
			with (
				self.subTest(value=value),
				patch(
					'core.commands.folder_refresh.get_setting', return_value=value
				)
			):
				self.assertEqual(expected, _is_enabled(LOCAL))


class ToggleFolderRefreshTest(TestCase):
	def test_toggle_saves_value_and_updates_all_timers(self):
		with (
			patch('core.commands.folder_refresh.get_setting', return_value=False),
			patch('core.commands.folder_refresh.save_setting') as save_setting,
			patch(
				'core.commands.folder_refresh._update_all_timers'
			) as update_all_timers,
			patch(
				'core.commands.folder_refresh.show_status_message'
			) as show_status_message
		):
			_toggle(NETWORK)

		save_setting.assert_called_once_with(
			'Core Settings.json', NETWORK.enabled_key, True
		)
		update_all_timers.assert_called_once_with()
		show_status_message.assert_called_once_with(
			'Network folder refresh: on (every 5 s)', timeout_secs=3
		)

	def test_toggle_off_preserves_the_saved_interval(self):
		with (
			patch('core.commands.folder_refresh.get_setting', return_value=True),
			patch('core.commands.folder_refresh.save_setting') as save_setting,
			patch('core.commands.folder_refresh._update_all_timers'),
			patch(
				'core.commands.folder_refresh.show_status_message'
			) as show_status_message
		):
			_toggle(FTP)

		save_setting.assert_called_once_with(
			'Core Settings.json', FTP.enabled_key, False
		)
		show_status_message.assert_called_once_with(
			'FTP folder refresh: off', timeout_secs=3
		)
