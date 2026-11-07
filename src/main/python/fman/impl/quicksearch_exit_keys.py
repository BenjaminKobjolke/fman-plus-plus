"""Quicksearch exit results and key binding matching."""
from dataclasses import dataclass

from fman.impl.util.qt.key_event import QtKeyEvent


@dataclass(frozen=True)
class QuicksearchExit:
	"""A quicksearch closed to switch to another command."""

	query: str
	command: str


def find_exit_key(exit_keys, key, modifiers):
	"""Return the first configured binding matching a key event, if any."""
	key_event = QtKeyEvent(key, modifiers)
	for binding in exit_keys:
		if key_event.matches(binding):
			return binding
	return None
