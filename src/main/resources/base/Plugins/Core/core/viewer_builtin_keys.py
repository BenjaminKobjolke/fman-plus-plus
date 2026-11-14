"""Look up the default keys handled directly by the text viewer."""

from core.textviewer_cursor import COMMANDS as CURSOR_COMMANDS
from core.textviewer_search import COMMANDS as SEARCH_COMMANDS


def builtin_key(command_name):
	"""Return a viewer pseudo-command's built-in key, or an empty string."""
	# Esc also closes the viewer, so it must not be offered for removal.
	commands = SEARCH_COMMANDS + CURSOR_COMMANDS
	return next((default for name, default, *_rest in commands
		if name == command_name and name != 'text_search_exit'), '')
