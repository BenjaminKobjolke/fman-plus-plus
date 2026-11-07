from core.plugin_list import PluginListEntry, PluginOs, PluginSource
from core.fman_api import FmanApiError
from core.plugin_sync import SyncState, record_install, record_remove
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch


class PluginSyncHooksTest(TestCase):
	def setUp(self):
		self.client = Mock()
		self.signed_in = patch(
			'core.plugin_sync.signed_in_client', return_value=self.client
		)
		self.signed_in.start()
		self.addCleanup(self.signed_in.stop)
		self.status = patch('core.plugin_sync.show_status_message')
		self.status_mock = self.status.start()
		self.addCleanup(self.status.stop)

	def test_install_is_uploaded_and_marked_as_synced(self):
		entry = _entry('New')
		with TemporaryDirectory() as directory, patch(
			'core.plugin_sync.DATA_DIRECTORY', directory
		):
			record_install(entry)
			self.client.put_plugin.assert_called_once_with(entry)
			self.assertEqual({'New'}, SyncState.load().synced_names)

	def test_remove_is_deleted_and_removed_from_synced_state(self):
		with TemporaryDirectory() as directory, patch(
			'core.plugin_sync.DATA_DIRECTORY', directory
		):
			SyncState(synced_names={'Existing'}).save()
			record_remove('Existing')
			self.client.delete_plugin.assert_called_once_with('Existing')
			self.assertEqual(set(), SyncState.load().synced_names)

	def test_offline_install_shows_repairable_status(self):
		self.client.put_plugin.side_effect = FmanApiError('offline')
		entry = _entry('Offline')
		with TemporaryDirectory() as directory, patch(
			'core.plugin_sync.DATA_DIRECTORY', directory
		):
			record_install(entry)
			self.assertEqual(set(), SyncState.load().synced_names)
		self.status_mock.assert_called_once()


def _entry(name):
	return PluginListEntry(
		name, PluginSource.GITHUB, 'https://github.com/example/' + name,
		'v1', PluginOs.WINDOWS, '2.1.4'
	)
