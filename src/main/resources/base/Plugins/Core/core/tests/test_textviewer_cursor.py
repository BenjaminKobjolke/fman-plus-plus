from core.textviewer_cursor import ViewerCursor
from fman.impl.util.qt.key_event import QtKeyEvent
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from unittest import TestCase
from unittest.mock import patch

class _FakeScrollBar:
	_MAXIMUM = 999

	def __init__(self):
		self.value = None

	def maximum(self):
		return self._MAXIMUM

	def setValue(self, value):
		self.value = value

class _FakeView:
	# Stand-in for PaneTextView: ViewerCursor only moves its cursor and its
	# scrollbar, so no QApplication (and no real widget) is needed.
	def __init__(self):
		self.moves = []
		self.scrollbar = _FakeScrollBar()

	def moveCursor(self, operation):
		self.moves.append(operation)

	def verticalScrollBar(self):
		return self.scrollbar

class _FakeBase:
	# Replaces the QPlainTextEdit the paging actions hand their synthesized
	# key event to, recording which key the real base class would have seen.
	def __init__(self):
		self.keys = []

	def keyPressEvent(self, view, event):
		self.keys.append((view, event.key()))

class ViewerCursorTest(TestCase):
	def setUp(self):
		self.bindings = []
		self.base = _FakeBase()
		patches = {
			'load_json': lambda *_args, **_kwargs: self.bindings,
			'QPlainTextEdit': self.base,
		}
		for name, replacement in patches.items():
			patcher = patch('core.textviewer_cursor.' + name, replacement)
			patcher.start()
			self.addCleanup(patcher.stop)
		self.view = _FakeView()
		self.cursor_keys = ViewerCursor(self.view)

	def _press(self, key, modifiers=Qt.NoModifier):
		return self.cursor_keys.handle_key(QtKeyEvent(key, modifiers))

	def test_home_goes_to_top(self):
		self.assertTrue(self._press(Qt.Key_Home))
		self.assertEqual([QTextCursor.Start], self.view.moves)

	def test_end_goes_to_bottom(self):
		self.assertTrue(self._press(Qt.Key_End))
		self.assertEqual([QTextCursor.End], self.view.moves)
		self.assertEqual(_FakeScrollBar._MAXIMUM, self.view.scrollbar.value)

	def test_page_keys_use_native_paging(self):
		self.assertTrue(self._press(Qt.Key_PageUp))
		self.assertTrue(self._press(Qt.Key_PageDown))
		self.assertEqual(
			[(self.view, Qt.Key_PageUp), (self.view, Qt.Key_PageDown)],
			self.base.keys
		)
		self.assertEqual([], self.view.moves)

	def test_modified_home_falls_through(self):
		# Shift+Home selects to the line start and Ctrl+Home is Qt's own
		# document jump - neither may be swallowed by the Home default.
		self.assertFalse(self._press(Qt.Key_Home, Qt.ShiftModifier))
		self.assertFalse(self._press(Qt.Key_Home, Qt.ControlModifier))
		self.assertEqual([], self.view.moves)

	def test_unrelated_key_falls_through(self):
		self.assertFalse(self._press(Qt.Key_A))
		self.assertEqual([], self.view.moves)

	def test_actions_hint_the_default_key(self):
		self.assertEqual(
			[
				('Go to top', 'Home', 'text_go_to_top'),
				('Go to bottom', 'End', 'text_go_to_bottom'),
				('Page up', 'PgUp', 'text_page_up'),
				('Page down', 'PgDown', 'text_page_down'),
			],
			[
				(title, hint, name)
				for title, _action, hint, name in self.cursor_keys.actions()
			]
		)

	def test_actions_follow_a_rebind(self):
		self.bindings = [{'keys': ['Ctrl+Home'], 'command': 'text_go_to_top'}]
		self.assertEqual('Ctrl+Home, Home', self.cursor_keys.actions()[0][2])

	def test_commands_bind_each_action_to_its_own_name(self):
		# Without the default-argument capture in commands(), every entry
		# would close over the last row of COMMANDS.
		commands = self.cursor_keys.commands()
		commands['text_go_to_top']()
		commands['text_page_up']()
		self.assertEqual([QTextCursor.Start], self.view.moves)
		self.assertEqual([(self.view, Qt.Key_PageUp)], self.base.keys)

	def test_every_palette_entry_is_bindable_under_the_same_name(self):
		# A palette entry whose command name has no binding counterpart would
		# be unbindable, and a bound key with no entry undiscoverable.
		self.assertEqual(
			set(self.cursor_keys.commands()),
			{
				name
				for _title, _action, _hint, name in self.cursor_keys.actions()
			}
		)
