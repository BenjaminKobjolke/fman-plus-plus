"""Build effective palette exit-key mappings and dispatch palette switches."""
from core.key_bindings import KEY_BINDINGS_FILE, get_shortcuts_for_command
from fman import load_json


GO_TO = 'go_to'
COMMAND_PALETTE = 'command_palette'
COMMAND_PREFIX = '>'


def strip_command_prefix(query):
	"""Remove the palette marker when it is present at the start."""
	if query.startswith(COMMAND_PREFIX):
		return query[len(COMMAND_PREFIX):]
	return query


def goto_query_exit(text):
	"""Switch Go To to the palette when the user types its marker."""
	if text.startswith(COMMAND_PREFIX):
		return COMMAND_PALETTE


def palette_query_exit(text):
	"""Switch back to Go To when the palette marker is removed."""
	if not text.startswith(COMMAND_PREFIX):
		return GO_TO


def palette_exit_keys(own_command, other_command):
	"""Map the other palette's shortcuts to switch and own shortcuts to close."""
	key_bindings = load_json(KEY_BINDINGS_FILE) or []
	result = {
		shortcut: other_command
		for shortcut in get_shortcuts_for_command(key_bindings, other_command)
	}
	result.update({
		shortcut: None
		for shortcut in get_shortcuts_for_command(key_bindings, own_command)
	})
	return result


def run_palette_switch(pane, exit):
	# shortcut: nesting is fine for human switching; change dispatch if loops grow deep.
	pane.run_command(exit.command, {
		'query': exit.query, 'continue_typing': exit.from_text
	})
