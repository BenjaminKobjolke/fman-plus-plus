import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

from core.fman_api import (
	FmanApiClient, FmanApiConflictError, FmanApiError, SyncedSettingsDocument,
)
from core.settings_sync import (
	SettingsSyncState, SyncedEntry, SyncedSettingsKind, content_hash,
)
from core import settings_sync_runner


class SettingsSyncRunnerTest(TestCase):
	def setUp(self):
		self.temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp_dir.cleanup)
		self.settings_dir = os.path.join(self.temp_dir.name, 'settings')
		self.data_dir = os.path.join(self.temp_dir.name, 'data')
		self.patches = [
			patch('core.settings_sync_runner.PLATFORM', 'Windows'),
			patch('core.settings_sync.DATA_DIRECTORY', self.data_dir),
			patch('core.user_bindings._SETTINGS_PLUGIN', self.settings_dir),
			patch('core.user_bindings.PLATFORM', 'Windows'),
			patch('core.user_bindings._reload_settings_plugin'),
			patch('core.settings_sync_runner.ask_conflict'),
			patch('core.settings_sync_runner.show_status_message'),
		]
		for item in self.patches:
			item.start()
			self.addCleanup(item.stop)
		self.client = Mock(spec=FmanApiClient)
		self.kind = SyncedSettingsKind.KEY_BINDINGS
		self.path = os.path.join(self.settings_dir, 'Key Bindings (Windows).json')

	def write_local(self, content):
		os.makedirs(self.settings_dir, exist_ok=True)
		with open(self.path, 'w', encoding='utf-8') as settings_file:
			json.dump(content, settings_file)

	def read_local(self):
		with open(self.path, encoding='utf-8') as settings_file:
			return json.load(settings_file)

	def document(self, content, revision=1):
		return SyncedSettingsDocument(
			'Windows', self.kind.value, revision, content,
			'2026-11-08T20:00:00+00:00'
		)

	def state(self):
		return SettingsSyncState.load()

	def save_entry(self, entry):
		state = self.state()
		state.entries[self.kind] = entry
		state.save()

	def test_first_sync_pulls_remote_and_records_state(self):
		remote = [{'keys': 'Ctrl+A', 'command': 'select_all'}]
		self.client.get_settings.return_value = self.document(remote, 4)

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.assertEqual(remote, self.read_local())
		self.assertEqual(
			SyncedEntry(4, content_hash(remote)), self.state().entries[self.kind]
		)
		self.client.put_settings.assert_not_called()

	def test_wrong_local_json_type_is_treated_as_empty(self):
		self.write_local({'not': 'a binding list'})
		self.client.get_settings.return_value = None

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.client.put_settings.assert_not_called()
		self.assertEqual({'not': 'a binding list'}, self.read_local())

	def test_local_edit_pushes_using_recorded_base_revision(self):
		original = [{'keys': 'Ctrl+A', 'command': 'select_all'}]
		changed = original + [{'keys': 'Ctrl+B', 'command': 'back'}]
		self.write_local(changed)
		self.save_entry(SyncedEntry(7, content_hash(original)))
		self.client.get_settings.return_value = self.document(original, 7)
		self.client.put_settings.return_value = self.document(changed, 8)

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.client.put_settings.assert_called_once_with(
			'Windows', self.kind.value, 7, changed
		)
		self.assertEqual(
			SyncedEntry(8, content_hash(changed)), self.state().entries[self.kind]
		)

	def test_conflict_keep_local_retries_with_current_revision(self):
		local = [{'keys': 'Ctrl+A'}]
		current = self.document([{'keys': 'Ctrl+B'}], 9)
		self.write_local(local)
		self.save_entry(SyncedEntry(8, content_hash([])))
		self.client.get_settings.return_value = self.document([], 8)
		self.client.put_settings.side_effect = [
			FmanApiConflictError(current), self.document(local, 10)
		]
		settings_sync_runner.ask_conflict.return_value = (
			settings_sync_runner.ConflictChoice.KEEP_LOCAL
		)

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.assertEqual(
			[8, 9],
			[call.args[2] for call in self.client.put_settings.call_args_list]
		)
		self.assertEqual(
			SyncedEntry(10, content_hash(local)), self.state().entries[self.kind]
		)

	def test_conflict_use_account_replaces_local_copy(self):
		local = [{'keys': 'Ctrl+A'}]
		remote = [{'keys': 'Ctrl+B'}]
		self.write_local(local)
		self.save_entry(SyncedEntry(3, content_hash([])))
		current = self.document(remote, 5)
		self.client.get_settings.return_value = self.document([], 3)
		self.client.put_settings.side_effect = FmanApiConflictError(current)
		settings_sync_runner.ask_conflict.return_value = (
			settings_sync_runner.ConflictChoice.USE_ACCOUNT
		)

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.assertEqual(remote, self.read_local())
		self.assertEqual(
			SyncedEntry(5, content_hash(remote)), self.state().entries[self.kind]
		)

	def test_conflict_combine_saves_and_pushes_local_precedence(self):
		local = [{'keys': 'Ctrl+A', 'command': 'local'}]
		remote = [{'keys': 'Ctrl+A', 'command': 'remote'}, {'keys': 'Ctrl+B'}]
		combined = [local[0], remote[1]]
		self.write_local(local)
		self.save_entry(SyncedEntry(3, content_hash([])))
		current = self.document(remote, 5)
		self.client.get_settings.return_value = self.document([], 3)
		self.client.put_settings.side_effect = [
			FmanApiConflictError(current), self.document(combined, 6)
		]
		settings_sync_runner.ask_conflict.return_value = (
			settings_sync_runner.ConflictChoice.COMBINE
		)

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.assertEqual(combined, self.read_local())
		self.assertEqual(
			('Windows', self.kind.value, 5, combined),
			self.client.put_settings.call_args_list[1].args
		)
		self.assertEqual(
			SyncedEntry(6, content_hash(combined)), self.state().entries[self.kind]
		)

	def test_picker_escape_leaves_local_and_state_unchanged(self):
		local = [{'keys': 'Ctrl+A'}]
		self.write_local(local)
		before = self.state().to_json()
		self.client.get_settings.return_value = self.document([{'keys': 'Ctrl+B'}], 5)
		settings_sync_runner.ask_conflict.return_value = None

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.assertEqual(local, self.read_local())
		self.assertEqual(before, self.state().to_json())
		self.client.put_settings.assert_not_called()

	def test_second_conflict_keeps_state_and_shows_status(self):
		local = [{'keys': 'Ctrl+A'}]
		self.write_local(local)
		self.save_entry(SyncedEntry(3, content_hash([])))
		before = self.state().to_json()
		self.client.get_settings.return_value = self.document([], 4)
		self.client.put_settings.side_effect = [
			FmanApiConflictError(self.document([], 5)),
			FmanApiConflictError(self.document([], 6)),
		]
		settings_sync_runner.ask_conflict.return_value = (
			settings_sync_runner.ConflictChoice.KEEP_LOCAL
		)

		settings_sync_runner.sync_settings(self.client, [self.kind])

		self.assertEqual(before, self.state().to_json())
		settings_sync_runner.show_status_message.assert_called_once()

	def test_record_change_when_signed_out_makes_no_api_calls(self):
		with patch('core.settings_sync_runner.signed_in_client', return_value=None):
			settings_sync_runner.record_settings_change(self.kind.file_name)

		self.client.get_settings.assert_not_called()
		self.client.put_settings.assert_not_called()

	def test_record_change_api_error_shows_status_and_keeps_local_file(self):
		local = [{'keys': 'Ctrl+A'}]
		self.write_local(local)
		self.client.get_settings.side_effect = FmanApiError('offline')
		with patch(
			'core.settings_sync_runner.signed_in_client', return_value=self.client
		):
			settings_sync_runner.record_settings_change(self.kind.file_name)

		self.assertEqual(local, self.read_local())
		settings_sync_runner.show_status_message.assert_called_once()


class SettingsConflictPickerTest(TestCase):
	def test_picker_lists_three_choices_and_escape_returns_none(self):
		picker = settings_sync_runner.SettingsConflictPicker(
			SyncedSettingsKind.KEY_BINDINGS
		)
		self.assertEqual(
			['Keep this computer\'s', 'Use the account\'s', 'Combine both'],
			picker.get_options()
		)
		self.assertIn('key bindings', picker.get_title())
		with patch('core.quicksearch_screen.show_quicksearch', return_value=None):
			self.assertIsNone(picker.choose())
		picker.on_selected('Combine both')
		self.assertEqual(
			settings_sync_runner.ConflictChoice.COMBINE, picker.choice
		)
