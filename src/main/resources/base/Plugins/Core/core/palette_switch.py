"""Build effective palette exit-key mappings and dispatch palette switches."""
from core.key_bindings import KEY_BINDINGS_FILE, get_shortcuts_for_command
from fman import load_json


GO_TO = 'go_to'
COMMAND_PALETTE = 'command_palette'
FILE_MENTION = 'file_mention'
COMMAND_PREFIX = '>'
MENTION_PREFIX = '@'


def _strip_prefix(query, prefix):
	if query.startswith(prefix):
		return query[len(prefix):]
	return query


def strip_command_prefix(query):
	"""Remove the palette marker when it is present at the start."""
	return _strip_prefix(query, COMMAND_PREFIX)


def strip_mention_prefix(query):
	"""Remove the file mention marker when it is present at the start."""
	return _strip_prefix(query, MENTION_PREFIX)


def goto_query_exit(text):
	"""Switch Go To to the palette or file mention when its marker is typed."""
	if text.startswith(COMMAND_PREFIX):
		return COMMAND_PALETTE
	if text.startswith(MENTION_PREFIX):
		return FILE_MENTION


def palette_query_exit(text):
	"""Switch back to Go To when the palette marker is removed."""
	if not text.startswith(COMMAND_PREFIX):
		return GO_TO


def mention_query_exit(text):
	"""Switch back to Go To when the file mention marker is removed."""
	if not text.startswith(MENTION_PREFIX):
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
