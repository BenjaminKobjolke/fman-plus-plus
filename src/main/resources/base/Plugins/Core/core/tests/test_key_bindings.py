from core.key_bindings import command_for_key_event, command_for_shortcut, \
	dispatch_bindable_command, get_shortcuts_for_command, DO_NOTHING
from fman.impl.util.qt.key_event import QtKeyEvent
from PyQt5.QtCore import Qt
import json
import os
from unittest import TestCase

class CommandForKeyEventTest(TestCase):
	_BINDINGS = [
		{'keys': ['M'], 'command': 'video_mute'},
		{'keys': ['Ctrl+R'], 'command': 'video_restart'},
	]

	def test_matches_bound_command(self):
		event = QtKeyEvent(Qt.Key_M, Qt.NoModifier)
		self.assertEqual(
			'video_mute',
			command_for_key_event(
				event, self._BINDINGS, ('video_mute', 'video_restart')
			),
		)

	def test_finds_command_regardless_of_command_names_order(self):
		# video_restart's shortcut (Ctrl+R) must resolve even when it's
		# listed after video_mute in command_names.
		event = QtKeyEvent(Qt.Key_R, Qt.ControlModifier)
		self.assertEqual(
			'video_restart',
			command_for_key_event(
				event, self._BINDINGS, ('video_mute', 'video_restart')
			),
		)

	def test_no_match_returns_none(self):
		event = QtKeyEvent(Qt.Key_Z, Qt.NoModifier)
		self.assertIsNone(
			command_for_key_event(
				event, self._BINDINGS, ('video_mute', 'video_restart')
			)
		)

class DispatchBindableCommandTest(TestCase):
	def test_calls_matched_command_and_returns_true(self):
		called = []
		commands = {'video_mute': lambda: called.append('video_mute')}
		event = QtKeyEvent(Qt.Key_M, Qt.NoModifier)
		bindings = [{'keys': ['M'], 'command': 'video_mute'}]
		self.assertTrue(dispatch_bindable_command(event, bindings, commands))
		self.assertEqual(['video_mute'], called)

	def test_no_match_returns_false_without_calling_anything(self):
		called = []
		commands = {'video_mute': lambda: called.append('video_mute')}
		event = QtKeyEvent(Qt.Key_Z, Qt.NoModifier)
		bindings = [{'keys': ['M'], 'command': 'video_mute'}]
		self.assertFalse(dispatch_bindable_command(event, bindings, commands))
		self.assertEqual([], called)

	def test_an_explicitly_unbound_key_is_swallowed(self):
		# The viewers' hardcoded fallback keys run after this lookup, so
		# "unbound" has to mean the keystroke stops here.
		called = []
		commands = {'video_toggle_pause': lambda: called.append('pause')}
		event = QtKeyEvent(Qt.Key_Space, Qt.NoModifier)
		bindings = [
			{'keys': ['Space'], 'command': DO_NOTHING},
			{'keys': ['Space'], 'command': 'video_toggle_pause'},
		]
		self.assertTrue(dispatch_bindable_command(event, bindings, commands))
		self.assertEqual([], called)

class CommandForShortcutTest(TestCase):
	_BINDINGS = [
		{'keys': ['M'], 'command': 'video_mute'},
		{'keys': ['M'], 'command': 'pack'},
	]

	def test_names_the_command_a_shortcut_runs(self):
		self.assertEqual('video_mute', command_for_shortcut(self._BINDINGS, 'M'))

	def test_first_match_wins_like_fmans_own_dispatch(self):
		# The second M binding is dead, so naming it would mislead the user.
		self.assertNotEqual('pack', command_for_shortcut(self._BINDINGS, 'M'))

	def test_an_unbound_shortcut_is_none(self):
		self.assertIsNone(command_for_shortcut(self._BINDINGS, 'Ctrl+Z'))

	def test_malformed_entries_are_skipped(self):
		bindings = ['nonsense', {'command': 'pack'}, {'keys': [], 'command': 'x'}]
		self.assertIsNone(command_for_shortcut(bindings, 'M'))

class GetShortcutsForCommandTest(TestCase):
	def test_no_shortcut(self):
		self._check([{'keys': ['Enter'], 'command': 'open'}], 'copy', [])
	def test_simple(self):
		self._check([{'keys': ['Enter'], 'command': 'open'}], 'open', ['Enter'])
	def test_two_shortcuts(self):
		self._check(
			[{'keys': ['Enter'], 'command': 'open'},
			 {'keys': ['Down'], 'command': 'open'}],
			'open', ['Enter', 'Down']
		)
	def test_shortcut_only_displayed_for_one_command(self):
		bindings = [
			{'keys': ['Enter'], 'command': 'open'},
			{'keys': ['Enter'], 'command': 'alternative'}
		]
		self._check(bindings, 'open', ['Enter'])
		self._check(bindings, 'alternative', [])
	def _check(self, key_bindings, command, expected_shortcuts):
		actual = list(get_shortcuts_for_command(key_bindings, command))
		self.assertEqual(expected_shortcuts, actual)

class KeypadSelectionBindingsTest(TestCase):
	def test_base_bindings_register_the_total_commander_keypad_set(self):
		path = os.path.join(
			os.path.dirname(__file__), '..', '..', 'Key Bindings.json'
		)
		with open(os.path.normpath(path), encoding='utf-8') as bindings_file:
			bindings = json.load(bindings_file)
		expected = [
			{'keys': ['Num++'], 'command': 'select_group'},
			{'keys': ['Num+-'], 'command': 'deselect_group'},
			{
				'keys': ['Num+*'], 'command': 'invert_selection',
				'args': {'files_only': True},
			},
			{
				'keys': ['Ctrl+Num++'], 'command': 'select_group',
				'args': {'mask': '*.*'},
			},
			{'keys': ['Ctrl+Num+-'], 'command': 'deselect'},
			{'keys': ['Alt+Num++'], 'command': 'select_same_extension'},
			{'keys': ['Alt+Num+-'], 'command': 'deselect_same_extension'},
		]
		self.assertTrue(all(binding in bindings for binding in expected))
		import core
		for binding in expected:
			command = binding['command']
			self.assertTrue(hasattr(core, ''.join(
				part.title() for part in command.split('_')
			)), command)
		self.assertTrue(QtKeyEvent(Qt.Key_Plus, Qt.KeypadModifier).matches('Num++'))
		self.assertFalse(QtKeyEvent(Qt.Key_Plus, Qt.NoModifier).matches('Num++'))
