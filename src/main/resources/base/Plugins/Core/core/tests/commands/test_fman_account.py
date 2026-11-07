from core.commands import fman_account as commands
from core.plugin_list import PluginListEntry, PluginOs, PluginSource
from core.plugin_sync import SyncPlan, SyncState
from fman import NO, YES
from unittest import TestCase
from unittest.mock import Mock, patch


class AccountCommandsTest(TestCase):
	def setUp(self):
		self.patches = {}
		for name in (
			'sign_in', 'clear_token', 'signed_in_client', 'SyncState.load',
			'compute_sync', 'PluginSyncDialog', 'show_alert',
			'show_status_message', 'entry_for_installed',
			'_get_thirdparty_plugins', 'install_zip', 'record_installation',
			'load_installed_plugin', 'remove_plugin_dir',
			'run_application_command', 'repo_for_location',
		):
			p = patch('core.commands.fman_account.' + name)
			self.patches[name] = p.start()
			self.addCleanup(p.stop)
		self.command = commands.SyncPlugins(None)
		self.client = Mock()
		self.patches['signed_in_client'].return_value = self.client
		self.client.get_plugin_list.return_value = ()
		self.client.download_release.return_value = b'zip'
		self.patches['SyncState.load'].return_value = SyncState()
		self.patches['compute_sync'].return_value = SyncPlan()
		self.patches['_get_thirdparty_plugins'].return_value = []

	def test_sign_in_shows_account_email(self):
		result = Mock(email='person@example.com')
		self.patches['sign_in'].return_value = result
		commands.SignInToFmanAccount(None)()
		self.patches['show_status_message'].assert_called_once_with(
			'Signed in to fman account: person@example.com'
		)

	def test_sign_out_clears_token(self):
		commands.SignOutOfFmanAccount(None)()
		self.patches['clear_token'].assert_called_once_with()

	def test_no_work_is_quiet(self):
		self.command(silent=True)
		self.patches['show_alert'].assert_not_called()
		self.patches['show_status_message'].assert_not_called()

	def test_signed_out_shows_status_and_stops(self):
		self.patches['signed_in_client'].return_value = None
		self.command(silent=True)
		self.patches['show_status_message'].assert_called_once_with(
			'Signed out of fman account'
		)
		self.patches['compute_sync'].assert_not_called()

	def test_upload_and_remote_delete_are_applied_without_prompts(self):
		entry = _entry('Upload')
		self.patches['compute_sync'].return_value = SyncPlan(
			to_upload=(entry,), to_delete=('Delete',)
		)
		self.command(silent=True)
		self.client.put_plugin.assert_called_once_with(entry)
		self.client.delete_plugin.assert_called_once_with('Delete')
		self.patches['PluginSyncDialog'].assert_not_called()
		self.patches['show_alert'].assert_not_called()

	def test_remote_install_uses_checked_entry_and_catalog_version(self):
		entry = _entry('Remote', source=PluginSource.CATALOG)
		self.patches['compute_sync'].return_value = SyncPlan(to_install=(entry,))
		dialog = self.patches['PluginSyncDialog'].return_value
		dialog.exec_.return_value = 1
		dialog.selected_entries.return_value = (entry,)
		self.patches['install_zip'].return_value = 'plugin-dir'
		self.patches['load_installed_plugin'].return_value = True
		self.command(silent=True)
		self.client.download_release.assert_called_once_with('Remote', 'v1')
		self.patches['install_zip'].assert_called_once_with('Remote', b'zip')
		self.patches['record_installation'].assert_called_once_with(
			'plugin-dir', 'Remote', 'v1', source='catalog'
		)

	def test_remote_gitlab_install_uses_location_and_source(self):
		entry = _entry('Remote', source=PluginSource.GITLAB)
		self.patches['compute_sync'].return_value = SyncPlan(to_install=(entry,))
		dialog = self.patches['PluginSyncDialog'].return_value
		dialog.exec_.return_value = 1
		dialog.selected_entries.return_value = (entry,)
		self.patches['install_zip'].return_value = 'plugin-dir'
		self.patches['repo_for_location'].return_value = Mock(
			download_zipball=Mock(return_value=b'zip')
		)
		self.command(silent=True)
		self.patches['repo_for_location'].assert_called_once_with(
			PluginSource.GITLAB, entry.location
		)
		self.patches['repo_for_location'].return_value.download_zipball.assert_called_once_with('v1')
		self.patches['record_installation'].assert_called_once_with(
			'plugin-dir', entry.location, 'v1', source='gitlab'
		)

	def test_declined_removal_leaves_plugin_installed(self):
		self.patches['compute_sync'].return_value = SyncPlan(
			to_remove=('Local',)
		)
		self.patches['show_alert'].return_value = NO
		self.command(silent=True)
		self.patches['show_alert'].assert_called_once()
		self.patches['remove_plugin_dir'].assert_not_called()

	def test_confirmed_removal_removes_plugins(self):
		self.patches['compute_sync'].return_value = SyncPlan(
			to_remove=('Local',)
		)
		self.patches['show_alert'].return_value = YES
		self.patches['_get_thirdparty_plugins'].return_value = ['plugins/Local']
		self.command(silent=True)
		self.patches['remove_plugin_dir'].assert_called_once_with('plugins/Local')

	def test_network_error_only_shows_status_message(self):
		self.client.get_plugin_list.side_effect = commands.FmanApiError('offline')
		self.command(silent=True)
		self.patches['show_status_message'].assert_called_once()
		self.patches['show_alert'].assert_not_called()

	def test_startup_listener_runs_once_silently(self):
		commands._STARTUP_SYNC_STARTED = False
		listener = commands.PluginSyncOnStartup(None)
		listener.on_path_changed()
		listener.on_path_changed()
		self.patches['run_application_command'].assert_called_once_with(
			'Sync plugins', {'silent': True}
		)
		commands._STARTUP_SYNC_STARTED = False


def _entry(name, source=PluginSource.GITHUB):
	if source == PluginSource.CATALOG:
		location = name
	elif source == PluginSource.GITLAB:
		location = 'https://gitlab.com/example/' + name
	else:
		location = 'https://github.com/example/' + name
	return PluginListEntry(
		name, source, location, 'v1', PluginOs.WINDOWS, '2.1.4'
	)
