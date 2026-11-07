from core.plugin_list import PluginListEntry, PluginOs, PluginSource
from core.plugin_sync import SyncState, compute_sync
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import json


class ComputeSyncTest(TestCase):
	def setUp(self):
		self.local = self._entry('Local')
		self.remote = self._entry('Remote')
		self.state = SyncState(synced_names={'Shared'})

	def test_finds_remote_install_and_local_upload(self):
		plan = compute_sync(
			{'Remote': self.remote, 'Shared': self._entry('Shared')},
			{'Local': self.local, 'Shared': self._entry('Shared')},
			self.state, PluginOs.WINDOWS
		)
		self.assertEqual((self.remote,), plan.to_install)
		self.assertEqual((self.local,), plan.to_upload)
		self.assertEqual((), plan.to_remove)
		self.assertEqual((), plan.to_delete)

	def test_finds_remote_removal_and_local_deletion(self):
		plan = compute_sync(
			{'LocalRemoval': self._entry('LocalRemoval')},
			{'RemoteRemoval': self._entry('RemoteRemoval')},
			SyncState(synced_names={'LocalRemoval', 'RemoteRemoval'}),
			PluginOs.WINDOWS
		)
		self.assertEqual(('RemoteRemoval',), plan.to_remove)
		self.assertEqual(('LocalRemoval',), plan.to_delete)

	def test_does_not_upload_source_less_local_plugins(self):
		plan = compute_sync({}, {'Manual': None}, SyncState(), PluginOs.WINDOWS)
		self.assertEqual((), plan.to_upload)

	def test_server_removed_plugin_is_not_treated_as_a_new_local_install(self):
		local = self._entry('RemovedRemotely')
		plan = compute_sync(
			{}, {'RemovedRemotely': local},
			SyncState(synced_names={'RemovedRemotely'}), PluginOs.WINDOWS
		)
		self.assertEqual(('RemovedRemotely',), plan.to_remove)
		self.assertEqual((), plan.to_upload)

	def test_other_os_remote_plugin_is_still_offered_for_confirmation(self):
		remote = self._entry('MacOnly', os=PluginOs.MAC)
		plan = compute_sync(
			{'MacOnly': remote}, {}, SyncState(), PluginOs.WINDOWS
		)
		self.assertEqual((remote,), plan.to_install)

	def test_keeps_local_removal_pending_while_offline(self):
		state = SyncState(synced_names={'RemovedHere'})
		plan = compute_sync(None, {}, state, PluginOs.WINDOWS)
		self.assertEqual(('RemovedHere',), plan.to_delete)

	def test_ignored_version_stays_suppressed_until_remote_version_changes(self):
		remote_v1 = self._entry('Remote', version='v1')
		remote_v2 = self._entry('Remote', version='v2')
		state = SyncState(ignored={'Remote': 'v1'})
		unchanged = compute_sync(
			{'Remote': remote_v1}, {}, state, PluginOs.WINDOWS
		)
		changed = compute_sync(
			{'Remote': remote_v2}, {}, state, PluginOs.WINDOWS
		)
		self.assertEqual((), unchanged.to_install)
		self.assertEqual((remote_v2,), changed.to_install)

	def test_include_ignored_offers_same_version_again(self):
		remote = self._entry('Remote', version='v1')
		plan = compute_sync(
			{'Remote': remote}, {}, SyncState(ignored={'Remote': 'v1'}),
			PluginOs.WINDOWS, include_ignored=True
		)
		self.assertEqual((remote,), plan.to_install)

	def test_does_not_upload_a_local_entry_tagged_for_another_os(self):
		local = self._entry('Local', os=PluginOs.MAC)
		plan = compute_sync({}, {'Local': local}, SyncState(), PluginOs.WINDOWS)
		self.assertEqual((), plan.to_upload)

	def _entry(self, name, version='v1', os=PluginOs.WINDOWS):
		return PluginListEntry(
			name, PluginSource.GITHUB, 'https://github.com/example/' + name,
			version, os, '2.1.4'
		)


class SyncStateTest(TestCase):
	def test_missing_state_file_is_empty(self):
		with TemporaryDirectory() as data_directory, \
				patch('core.plugin_sync.DATA_DIRECTORY', data_directory):
			self.assertEqual(SyncState(), SyncState.load())

	def test_broken_state_file_is_empty(self):
		with TemporaryDirectory() as data_directory, \
				patch('core.plugin_sync.DATA_DIRECTORY', data_directory):
			path = join(data_directory, 'Local', 'Plugin Sync.json')
			from os import makedirs
			makedirs(join(data_directory, 'Local'))
			with open(path, 'w', encoding='utf-8') as state_file:
				state_file.write('{broken')
			self.assertEqual(SyncState(), SyncState.load())

	def test_invalid_state_shape_is_empty(self):
		with TemporaryDirectory() as data_directory, \
				patch('core.plugin_sync.DATA_DIRECTORY', data_directory):
			path = join(data_directory, 'Local', 'Plugin Sync.json')
			from os import makedirs
			makedirs(join(data_directory, 'Local'))
			with open(path, 'w', encoding='utf-8') as state_file:
				json.dump({'synced_names': 'not a list', 'ignored': []}, state_file)
			self.assertEqual(SyncState(), SyncState.load())

	def test_save_and_load_round_trip(self):
		state = SyncState(synced_names={'One', 'Two'}, ignored={'Other': 'v2'})
		with TemporaryDirectory() as data_directory, \
				patch('core.plugin_sync.DATA_DIRECTORY', data_directory):
			state.save()
			self.assertEqual(state, SyncState.load())
			with open(
				join(data_directory, 'Local', 'Plugin Sync.json'), encoding='utf-8'
			) as f:
				self.assertEqual(
					{'ignored': {'Other': 'v2'}, 'synced_names': ['One', 'Two']},
					json.load(f)
				)
