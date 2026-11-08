from core.binding_editor import edit_key_bindings
from core.key_bindings import KEY_BINDINGS_FILE
from unittest import TestCase
from unittest.mock import patch

_MUTE = 'video_mute'

class _Screens:

	"""
	Drives the menu chain without Qt, like tests/test_keyword_editor.py:
	show_quicksearch is a queue of answers, one per screen that opens - a string
	picks that option, None means Escape. capture_shortcut is a queue too, so a
	test says which key the user "pressed" without a dialog.
	"""

	def __init__(self, answers, user, shipped=None, captured=None, confirm=True):
		self._answers = list(answers)
		self.user = list(user)
		self._shipped = list(shipped or [])
		self._captured = list(captured or [])
		self._confirm = confirm
		self.shown = []
		self.alerts = []
		self.sync_calls = []
	def show_quicksearch(self, get_items, *_args, **_kwargs):
		options = [item.value for item in get_items('')]
		self.shown.append(options)
		answer = self._answers.pop(0) if self._answers else None
		if answer is None:
			return None
		return '', answer
	def capture_shortcut(self, _prompt):
		return self._captured.pop(0) if self._captured else None
	def load_json(self, _name, default=None):
		# What fman merges: the user's bindings win, so they come first.
		return self.user + self._shipped
	def load_user_bindings(self, _bindings_file):
		return list(self.user)
	def save_user_bindings(self, _bindings_file, bindings):
		self.user = list(bindings)
	def show_alert(self, text, *_args, **_kwargs):
		self.alerts.append(text)
		return 1 if self._confirm else 2

def _run(
	answers, user, shipped=None, captured=None, confirm=True, command=_MUTE,
	title='Mute', bindings_file=KEY_BINDINGS_FILE
):
	screens = _Screens(answers, user, shipped, captured, confirm)
	with patch(
		'core.quicksearch_screen.show_quicksearch',
		side_effect=screens.show_quicksearch
	), patch(
		'core.binding_editor.capture_shortcut',
		side_effect=screens.capture_shortcut
	), patch(
		'core.binding_editor.load_json', side_effect=screens.load_json
	), patch(
		'core.binding_editor.show_alert', side_effect=screens.show_alert
	), patch(
		'core.binding_editor.load_user_bindings',
		side_effect=screens.load_user_bindings
	), patch(
		'core.binding_editor.save_user_bindings',
		side_effect=screens.save_user_bindings
	), patch(
		'core.user_bindings.load_user_bindings',
		side_effect=screens.load_user_bindings
	), patch(
		'core.user_bindings.load_json', side_effect=screens.load_json
	), patch(
		'core.binding_editor.YES', 1
	), patch(
		'core.binding_editor.NO', 2
	), patch(
		'core.binding_editor.record_settings_change',
		side_effect=lambda file_name: screens.sync_calls.append(file_name)
	):
		edit_key_bindings(command, title, bindings_file)
	return screens

def _binding(shortcut, command=_MUTE):
	return {'keys': [shortcut], 'command': command}

class BindingListTest(TestCase):

	def test_lists_add_then_the_shortcuts(self):
		screens = _run([None], [_binding('M')], [_binding('Ctrl+M')])
		self.assertEqual(
			['Add shortcut...', 'M  (yours)', 'Ctrl+M  (default)'],
			screens.shown[0]
		)
	def test_a_command_without_shortcuts_still_offers_add(self):
		screens = _run([None], [])
		self.assertEqual(['Add shortcut...'], screens.shown[0])
	def test_no_command_name_shows_nothing(self):
		screens = _run([None], [], command='')
		self.assertEqual([], screens.shown)
	def test_shortcuts_of_other_commands_are_not_listed(self):
		screens = _run([None], [_binding('M', 'pack')])
		self.assertEqual(['Add shortcut...'], screens.shown[0])

class AddShortcutTest(TestCase):

	def test_adds_the_captured_shortcut(self):
		screens = _run(['Add shortcut...', None], [], captured=['Ctrl+Alt+P'])
		self.assertEqual([_binding('Ctrl+Alt+P')], screens.user)
		self.assertEqual([KEY_BINDINGS_FILE], screens.sync_calls)
	def test_the_new_binding_is_prepended(self):
		# fman dispatches first match wins, so a new binding only beats an
		# existing one if it comes first.
		screens = _run(
			['Add shortcut...', None], [_binding('M')], captured=['Ctrl+Alt+P']
		)
		self.assertEqual(
			[_binding('Ctrl+Alt+P'), _binding('M')], screens.user
		)
	def test_cancelled_capture_saves_nothing(self):
		screens = _run(['Add shortcut...', None], [_binding('M')])
		self.assertEqual([_binding('M')], screens.user)
	def test_the_list_reopens_after_adding(self):
		screens = _run(['Add shortcut...', None], [], captured=['Ctrl+Alt+P'])
		self.assertEqual(
			['Add shortcut...', 'Ctrl+Alt+P  (yours)'], screens.shown[-1]
		)
	def test_duplicate_is_not_added_twice(self):
		screens = _run(
			['Add shortcut...', None], [_binding('M')], captured=['M']
		)
		self.assertEqual([_binding('M')], screens.user)

class ConflictTest(TestCase):

	def test_a_taken_shortcut_asks_first(self):
		screens = _run(
			['Add shortcut...', None], [], [_binding('F5', 'copy')],
			captured=['F5']
		)
		self.assertEqual(1, len(screens.alerts))
		self.assertIn('copy', screens.alerts[0])
	def test_confirming_binds_it_anyway(self):
		screens = _run(
			['Add shortcut...', None], [], [_binding('F5', 'copy')],
			captured=['F5']
		)
		self.assertEqual([_binding('F5')], screens.user)
	def test_declining_leaves_it_alone(self):
		screens = _run(
			['Add shortcut...', None], [], [_binding('F5', 'copy')],
			captured=['F5'], confirm=False
		)
		self.assertEqual([], screens.user)
	def test_a_free_shortcut_asks_nothing(self):
		screens = _run(['Add shortcut...', None], [], captured=['Ctrl+Alt+P'])
		self.assertEqual([], screens.alerts)

class RemoveShortcutTest(TestCase):

	def test_binding_menu_offers_remove_and_go_back(self):
		screens = _run(['M  (yours)', None], [_binding('M')])
		self.assertEqual(['Remove', 'Go back'], screens.shown[1])
	def test_removing_a_user_binding_deletes_it(self):
		screens = _run(
			['M  (yours)', 'Remove', None], [_binding('M'), _binding('N')]
		)
		self.assertEqual([_binding('N')], screens.user)
		self.assertEqual([KEY_BINDINGS_FILE], screens.sync_calls)
	def test_removing_a_shipped_default_shadows_it(self):
		# The shipped files are never written to, so the only way to unbind is
		# a higher-priority binding that does nothing.
		screens = _run(['F5  (default)', 'Remove', None], [], [_binding('F5')])
		self.assertEqual([_binding('F5', 'do_nothing')], screens.user)
	def test_go_back_keeps_the_shortcut(self):
		screens = _run(['M  (yours)', 'Go back', None], [_binding('M')])
		self.assertEqual([_binding('M')], screens.user)
		self.assertEqual(
			['Add shortcut...', 'M  (yours)'], screens.shown[-1]
		)
	def test_escape_on_the_binding_menu_returns_to_the_list(self):
		screens = _run(['M  (yours)', None, None], [_binding('M')])
		self.assertEqual(
			['Add shortcut...', 'M  (yours)'], screens.shown[-1]
		)

class MalformedFileTest(TestCase):

	"""
	The binding files are user-editable, so the editor must survive shapes
	get_shortcuts_for_command already tolerates - see tests/test_key_bindings.py.
	"""

	def test_malformed_entries_are_ignored(self):
		screens = _run(
			[None], [{'command': _MUTE}, 'nonsense', _binding('M')]
		)
		self.assertEqual(
			['Add shortcut...', 'M  (yours)'], screens.shown[0]
		)
