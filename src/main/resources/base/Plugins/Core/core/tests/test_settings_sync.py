from core.fman_api import SyncedSettingsDocument
from core.settings_sync import (
	SettingsSyncState, SyncedEntry, SyncedSettingsKind, SyncAction, combine,
	content_hash, decide,
)
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import json


class SettingsSyncDecisionTest(TestCase):
	def test_first_sync_pulls_nonempty_remote_when_local_is_empty(self):
		remote = _document([{'keys': 'Ctrl+A'}])

		self.assertEqual(
			SyncAction.PULL,
			decide([], remote, None)
		)

	def test_first_sync_with_equal_content_does_nothing(self):
		remote = _document([{'keys': 'Ctrl+A'}])

		self.assertEqual(SyncAction.NOTHING, decide(remote.content, remote, None))

	def test_first_sync_with_two_different_nonempty_values_asks(self):
		remote = _document([{'keys': 'Ctrl+B'}])

		self.assertEqual(
			SyncAction.ASK, decide([{'keys': 'Ctrl+A'}], remote, None)
		)

	def test_first_sync_without_remote_pushes_nonempty_local_content(self):
		self.assertEqual(SyncAction.PUSH, decide([{'keys': 'Ctrl+A'}], None, None))

	def test_first_sync_without_remote_and_empty_local_does_nothing(self):
		self.assertEqual(SyncAction.NOTHING, decide([], None, None))

	def test_first_sync_does_not_silently_replace_local_with_empty_remote(self):
		self.assertEqual(
			SyncAction.ASK, decide([{'keys': 'Ctrl+A'}], _document([]), None)
		)

	def test_tracked_sync_does_nothing_when_neither_side_changed(self):
		local = [{'keys': 'Ctrl+A'}]
		self.assertEqual(
			SyncAction.NOTHING,
			decide(local, _document(local, revision=2), _entry(2, local))
		)

	def test_tracked_sync_pulls_when_only_remote_changed(self):
		local = [{'keys': 'Ctrl+A'}]
		remote = [{'keys': 'Ctrl+B'}]
		self.assertEqual(
			SyncAction.PULL,
			decide(local, _document(remote, revision=3), _entry(2, local))
		)

	def test_tracked_sync_pushes_when_only_local_changed(self):
		local = [{'keys': 'Ctrl+B'}]
		remote = [{'keys': 'Ctrl+A'}]
		self.assertEqual(
			SyncAction.PUSH,
			decide(local, _document(remote, revision=2), _entry(2, remote))
		)

	def test_both_changed_to_same_content_does_nothing(self):
		changed = [{'keys': 'Ctrl+B'}]
		previous = [{'keys': 'Ctrl+A'}]
		self.assertEqual(
			SyncAction.NOTHING,
			decide(changed, _document(changed, revision=3), _entry(2, previous))
		)

	def test_tracked_sync_asks_when_both_sides_changed_differently(self):
		previous = [{'keys': 'Ctrl+A'}]
		self.assertEqual(
			SyncAction.ASK,
			decide(
				[{'keys': 'Ctrl+B'}],
				_document([{'keys': 'Ctrl+C'}], revision=3),
				_entry(2, previous),
			)
		)


class SettingsSyncCombineTest(TestCase):
	def test_combines_bindings_with_local_precedence_and_order(self):
		local = [
			{'keys': ['Ctrl+A'], 'command': 'Local'},
			{'keys': ['Ctrl+B'], 'command': 'Local B'},
		]
		remote = [
			{'keys': ['Ctrl+A'], 'command': 'Remote'},
			{'keys': ['Ctrl+C'], 'command': 'Remote C'},
		]

		self.assertEqual(
			[
				{'keys': ['Ctrl+A'], 'command': 'Local'},
				{'keys': ['Ctrl+B'], 'command': 'Local B'},
				{'keys': ['Ctrl+C'], 'command': 'Remote C'},
			],
			combine(SyncedSettingsKind.KEY_BINDINGS, local, remote),
		)

	def test_combines_objects_with_local_values_winning(self):
		self.assertEqual(
			{'Open': 'Local title', 'Copy': 'Copy', 'Paste': 'Paste'},
			combine(
				SyncedSettingsKind.COMMAND_TITLES,
				{'Open': 'Local title', 'Copy': 'Copy'},
				{'Open': 'Remote title', 'Paste': 'Paste'},
			),
		)

	def test_every_kind_maps_to_its_file_and_empty_content(self):
		expected = {
			'Key Bindings.json': (SyncedSettingsKind.KEY_BINDINGS, []),
			'Viewer Key Bindings.json': (SyncedSettingsKind.VIEWER_KEY_BINDINGS, []),
			'Command Titles.json': (SyncedSettingsKind.COMMAND_TITLES, {}),
			'Command Keywords.json': (SyncedSettingsKind.COMMAND_KEYWORDS, {}),
		}

		self.assertEqual(
			{kind for kind, _ in expected.values()}, set(SyncedSettingsKind)
		)
		for file_name, (kind, empty_value) in expected.items():
			with self.subTest(file_name=file_name):
				self.assertEqual(file_name, kind.file_name)
				self.assertEqual(kind, SyncedSettingsKind.for_file(file_name))
				self.assertEqual(empty_value, kind.empty_value)
		self.assertIsNone(SyncedSettingsKind.for_file('Other.json'))


class SettingsSyncStateTest(TestCase):
	def test_missing_state_file_loads_as_empty(self):
		with TemporaryDirectory() as data_directory, patch(
			'core.settings_sync.DATA_DIRECTORY', data_directory
		):
			self.assertEqual(SettingsSyncState(), SettingsSyncState.load())

	def test_state_saves_and_loads_round_trip(self):
		state = SettingsSyncState({
			SyncedSettingsKind.KEY_BINDINGS: _entry(3, [{'keys': 'Ctrl+A'}]),
			SyncedSettingsKind.COMMAND_TITLES: _entry(1, {'Open': 'Open'}),
		})

		with TemporaryDirectory() as data_directory, patch(
			'core.settings_sync.DATA_DIRECTORY', data_directory
		):
			state.save()
			self.assertEqual(state, SettingsSyncState.load())
			with open(
				join(data_directory, 'Local', 'Settings Sync.json'), encoding='utf-8'
			) as state_file:
				self.assertEqual(
					{
						'key_bindings': {
							'revision': 3,
							'content_hash': content_hash([{'keys': 'Ctrl+A'}]),
						},
						'command_titles': {
							'revision': 1,
							'content_hash': content_hash({'Open': 'Open'}),
						},
					},
					json.load(state_file),
				)

	def test_corrupt_state_file_loads_as_empty(self):
		with TemporaryDirectory() as data_directory, patch(
			'core.settings_sync.DATA_DIRECTORY', data_directory
		):
			path = join(data_directory, 'Local', 'Settings Sync.json')
			from os import makedirs
			makedirs(join(data_directory, 'Local'))
			with open(path, 'w', encoding='utf-8') as state_file:
				state_file.write('{broken')
			self.assertEqual(SettingsSyncState(), SettingsSyncState.load())


def _document(content, revision=1):
	return SyncedSettingsDocument(
		'Windows', 'key_bindings', revision, content, '2026-11-08T20:00:00+00:00'
	)


def _entry(revision, content):
	return SyncedEntry(revision, content_hash(content))
