from core.folder_tree_keys import is_tree_key, tree_move_key
from fman.impl.util.qt.key_event import QtKeyEvent
from PyQt5.QtCore import Qt
from unittest import TestCase


class IsTreeKeyTest(TestCase):
	def test_keeps_navigation_keys_and_shift_or_keypad_variants(self):
		for key, modifiers in (
			(Qt.Key_Left, Qt.NoModifier),
			(Qt.Key_Down, Qt.ShiftModifier),
			(Qt.Key_Up, Qt.KeypadModifier),
		):
			with self.subTest(key=key, modifiers=modifiers):
				self.assertTrue(is_tree_key(key, modifiers))

	def test_other_modifiers_and_non_navigation_keys_are_not_tree_keys(self):
		for key, modifiers in (
			(Qt.Key_Left, Qt.ControlModifier),
			(Qt.Key_Left, Qt.AltModifier),
			(Qt.Key_Delete, Qt.NoModifier),
		):
			with self.subTest(key=key, modifiers=modifiers):
				self.assertFalse(is_tree_key(key, modifiers))


class TreeMoveKeyTest(TestCase):
	def test_maps_move_cursor_binding_to_tree_key(self):
		bindings = [{'keys': ['Ctrl+J'], 'command': 'move_cursor_down'}]
		event = QtKeyEvent(Qt.Key_J, Qt.ControlModifier)

		self.assertEqual(Qt.Key_Down, tree_move_key(event, bindings))

	def test_unbound_key_has_no_tree_move(self):
		self.assertIsNone(tree_move_key(
			QtKeyEvent(Qt.Key_Z, Qt.NoModifier), []
		))
