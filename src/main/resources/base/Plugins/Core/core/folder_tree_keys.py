"""Keys the folder tree keeps for navigation and configurable cursor movement."""
from core.key_bindings import command_for_key_event
from PyQt5.QtCore import Qt
from fman.impl.util.qt.key_event import QtKeyEvent
from typing import Optional, TypedDict


class KeyBinding(TypedDict):
	keys: list[str]
	command: str


TREE_KEYS = {
	Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End,
	Qt.Key_PageUp, Qt.Key_PageDown,
}

MOVE_COMMANDS = {
	'move_cursor_down': Qt.Key_Down,
	'move_cursor_up': Qt.Key_Up,
	'move_cursor_home': Qt.Key_Home,
	'move_cursor_end': Qt.Key_End,
	'move_cursor_page_down': Qt.Key_PageDown,
	'move_cursor_page_up': Qt.Key_PageUp,
}


def is_tree_key(key: int, modifiers: Qt.KeyboardModifiers) -> bool:
	# Left and Right fold even when a plugin binds them, per Q #4382.
	return key in TREE_KEYS and not modifiers & ~(
		Qt.ShiftModifier | Qt.KeypadModifier
	)


def tree_move_key(
		key_event: QtKeyEvent, key_bindings: list[KeyBinding]) -> Optional[int]:
	command = command_for_key_event(
		key_event, key_bindings, list(MOVE_COMMANDS)
	)
	return MOVE_COMMANDS.get(command)
