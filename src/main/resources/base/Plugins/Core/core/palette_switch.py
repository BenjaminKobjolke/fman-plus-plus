"""Build effective palette exit-key mappings and dispatch palette switches."""
from core.key_bindings import KEY_BINDINGS_FILE, get_shortcuts_for_command
from fman import load_json


GO_TO = 'go_to'
COMMAND_PALETTE = 'command_palette'


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
	pane.run_command(exit.command, {'query': exit.query})
