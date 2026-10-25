from core.textviewer_zoom import (
	change_view_font_size, reset_view_font_size, zoom_actions, zoom_delta_for,
)
from core.viewer_navigation import ViewerAction
from core.tests.viewer_stubs import StubPane
from fman.impl.util.qt.key_event import QtKeyEvent
from PyQt5.QtCore import Qt
from unittest import TestCase
from unittest.mock import patch

class ZoomDeltaForTest(TestCase):
	# Fake merged Key Bindings.json content, standing in for whatever the
	# user actually has configured (defaults or a rebind) - zoom_delta_for
	# must key off this, never a hardcoded Alt+Up/Alt+Down.
	_BINDINGS = [
		{'keys': ['Alt+Up'], 'command': 'increase_pane_font_size'},
		{'keys': ['Alt+Down'], 'command': 'decrease_pane_font_size'},
	]

	def test_matches_configured_increase_shortcut(self):
		event = QtKeyEvent(Qt.Key_Up, Qt.AltModifier)
		self.assertEqual(+1, zoom_delta_for(event, self._BINDINGS))

	def test_matches_configured_decrease_shortcut(self):
		event = QtKeyEvent(Qt.Key_Down, Qt.AltModifier)
		self.assertEqual(-1, zoom_delta_for(event, self._BINDINGS))

	def test_unrelated_key_does_not_match(self):
		event = QtKeyEvent(Qt.Key_A, Qt.NoModifier)
		self.assertIsNone(zoom_delta_for(event, self._BINDINGS))

	def test_follows_a_user_rebind(self):
		# The whole point: if the user rebinds the shortcut, the OLD default
		# must stop matching and the NEW one must work instead.
		rebound = [
			{'keys': ['Ctrl+K'], 'command': 'increase_pane_font_size'},
		]
		old_default = QtKeyEvent(Qt.Key_Up, Qt.AltModifier)
		new_shortcut = QtKeyEvent(Qt.Key_K, Qt.ControlModifier)
		self.assertIsNone(zoom_delta_for(old_default, rebound))
		self.assertEqual(+1, zoom_delta_for(new_shortcut, rebound))

class ZoomActionsTest(TestCase):
	# Same fake merged Key Bindings.json as above.
	_BINDINGS = ZoomDeltaForTest._BINDINGS

	def _entries(self):
		# zoom_actions only reads `view` from inside its lambdas, so a bare
		# object stands in for the widget here.
		return [
			ViewerAction(*entry)
			for entry in zoom_actions(object(), lambda _size: None, self._BINDINGS)
		]

	def test_step_entries_edit_the_global_bindings_file(self):
		# Shift+Enter on these must rebind the pane font-size shortcut they
		# follow, which lives in Key Bindings.json - not the viewer file.
		increase, decrease, _reset = self._entries()
		self.assertEqual('increase_pane_font_size', increase.command_name)
		self.assertEqual('Key Bindings.json', increase.bindings_file)
		self.assertEqual('decrease_pane_font_size', decrease.command_name)
		self.assertEqual('Key Bindings.json', decrease.bindings_file)

	def test_step_entries_hint_at_their_configured_shortcut(self):
		increase, decrease, _reset = self._entries()
		self.assertEqual('Alt+Up', increase.hint)
		self.assertEqual('Alt+Down', decrease.hint)

	def test_reset_is_a_viewer_command_with_no_key(self):
		_increase, _decrease, reset = self._entries()
		self.assertEqual('text_reset_font_size', reset.command_name)
		self.assertEqual('', reset.hint)
		# Empty: the viewer file is open_viewer_palette's own default.
		self.assertEqual('', reset.bindings_file)

class ZoomStatusMessageTest(TestCase):
	# Reported from change/reset rather than from the palette entry, so the
	# Alt+Up/Alt+Down key path confirms the step too.
	class _FakeView:
		# Only `font` is read, and only to hand it to change_font_size -
		# which is patched out here, so it is never called.
		font = None
		def __init__(self):
			self._nav = type('Nav', (), {'pane': StubPane([])})()

	def test_a_step_reports_the_size_it_settled_on(self):
		view = self._FakeView()
		with patch('core.textviewer_zoom.change_font_size', return_value=15):
			change_view_font_size(view, lambda size: None, +1)
		self.assertEqual([('Font size 15', 3)], view._nav.pane.status_messages)

	def test_reset_says_so(self):
		view = self._FakeView()
		with patch('core.textviewer_zoom.reset_font_size'):
			reset_view_font_size(view, lambda size: None)
		self.assertEqual([('Font size reset', 3)], view._nav.pane.status_messages)
