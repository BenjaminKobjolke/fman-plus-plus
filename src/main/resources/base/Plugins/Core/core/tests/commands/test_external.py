from core.commands.external import OpenNativeFileManager
from core import os_
from core.tests.commands import FakePane
from fman import PLATFORM
from fman.url import as_human_readable
from unittest import TestCase, skipUnless
from unittest.mock import patch


class _FakePane(FakePane):
	def get_path(self):
		return self._url


class OpenNativeFileManagerTest(TestCase):
	@skipUnless(PLATFORM == 'Windows', 'Explorer is only available on Windows')
	def test_shipped_windows_default_opens_explorer_with_explicit_verb(self):
		settings = {'native_file_manager': {
			'args': ['start', 'explorer', '{curr_dir}'], 'shell': True}}
		with patch('core.os_.load_json', return_value=settings), \
				patch('core.os_.os.startfile') as startfile:
			os_.open_native_file_manager(r'C:\Temp')
		startfile.assert_called_once_with(r'C:\Temp', 'explore')

	@skipUnless(PLATFORM == 'Windows', 'Explorer is only available on Windows')
	def test_custom_windows_file_manager_setting_is_preserved(self):
		settings = {'native_file_manager': {'args': ['custom-manager', '{curr_dir}']}}
		with patch('core.os_.load_json', return_value=settings), \
				patch('core.os_._run_app_from_setting') as run_app, \
				patch('core.os_.os.startfile') as startfile:
			os_.open_native_file_manager(r'C:\Temp')
		run_app.assert_called_once_with(settings['native_file_manager'], r'C:\Temp')
		startfile.assert_not_called()

	def test_file_url_opens_native_file_manager(self):
		url = 'file://C:/Temp'
		with patch('core.commands.external.open_native_file_manager') as open_fm, \
				patch('core.commands.external.show_alert') as show_alert:
			OpenNativeFileManager(_FakePane(url=url))()
		open_fm.assert_called_once_with(as_human_readable(url))
		show_alert.assert_not_called()

	def test_non_file_url_shows_alert(self):
		with patch('core.commands.external.open_native_file_manager') as open_fm, \
				patch('core.commands.external.show_alert') as show_alert:
			OpenNativeFileManager(_FakePane(url='zip://C:/a.zip'))()
		open_fm.assert_not_called()
		show_alert.assert_called_once()

	@skipUnless(PLATFORM == 'Windows', 'network:// only exists on Windows')
	def test_network_overview_opens_explorer_network_page(self):
		with patch('core.commands.external.open_native_file_manager') as open_fm, \
				patch('core.commands.external.show_alert') as show_alert:
			OpenNativeFileManager(_FakePane(url='network://'))()
		open_fm.assert_called_once_with('shell:NetworkPlacesFolder')
		show_alert.assert_not_called()

	@skipUnless(PLATFORM == 'Windows', 'network:// only exists on Windows')
	def test_network_server_opens_unc_path(self):
		with patch('core.commands.external.open_native_file_manager') as open_fm, \
				patch('core.commands.external.show_alert') as show_alert:
			OpenNativeFileManager(_FakePane(url='network://SERVER1'))()
		open_fm.assert_called_once_with(r'\\SERVER1')
		show_alert.assert_not_called()
