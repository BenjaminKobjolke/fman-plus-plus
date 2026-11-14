"""
Looks up the shortcut(s) currently bound to a command in the merged,
effective key bindings (base + platform + user overrides, as returned by
fman.load_json('Key Bindings.json')) - i.e. whatever the user actually has
configured, not a hardcoded default. Shared by the global command palette
(hint display, core/commands/palette.py) and the text viewer (matching
keystrokes against the user's configured zoom shortcuts, and showing hints
in its own palette, core/textviewer.py). Kept in its own module since
the Core command package imports core/textviewer.py at module load
(core/commands/opening.py -> core/viewers.py) - the reverse import would
be circular.
"""
from fman import PLATFORM

# Viewer-only pseudo-commands (viewer_close, video_mute, etc.) live in their
# own file, never 'Key Bindings.json' - that one is loaded by fman's own
# sanitizer, which flags any command it doesn't recognize as a startup-alert
# error. A dedicated file sidesteps that entirely; see docs/KEYBINDINGS.md.
VIEWER_KEY_BINDINGS_FILE = 'Viewer Key Bindings.json'

# The global/file-list bindings, loaded and sanitized by fman itself.
KEY_BINDINGS_FILE = 'Key Bindings.json'

# A real, registered command that does nothing (core.commands.DoNothing), so a
# shipped default can be unbound by shadowing it with a higher-priority binding:
# the shipped files are never written to, and fman's sanitizer drops bindings
# whose command doesn't exist. See core/binding_editor.py.
DO_NOTHING = 'do_nothing'

_KEY_SYMBOLS_MAC = {
	'Cmd': '⌘', 'Alt': '⌥', 'Ctrl': '⌃', 'Shift': '⇧', 'Backspace': '⌫',
	'Up': '↑', 'Down': '↓', 'Left': '←', 'Right': '→', 'Enter': '↩'
}

def parse_bindings(key_bindings):
	"""
	The (shortcut, command) pairs of a Key Bindings file, skipping anything
	malformed - these files are hand-editable, so every reader has to survive
	whatever shape it finds. Only keys[0] is looked at, because that is all
	fman's own dispatch uses (Controller.handle_shortcut).
	"""
	for binding in key_bindings:
		try:
			shortcut = binding['keys'][0]
			command = binding['command']
		except (KeyError, IndexError, TypeError):
			continue
		if isinstance(shortcut, str):
			yield shortcut, command

def get_shortcuts_for_command(key_bindings, command):
	shortcuts_occupied_by_other_commands = set()
	for shortcut, binding_cmd in parse_bindings(key_bindings):
		if binding_cmd == command:
			if shortcut not in shortcuts_occupied_by_other_commands:
				yield shortcut
		shortcuts_occupied_by_other_commands.add(shortcut)

def command_for_shortcut(key_bindings, shortcut):
	"""
	The command a shortcut currently runs, or None. The inverse of
	get_shortcuts_for_command, and first-match-wins like fman's own dispatch,
	so it names the command the user would actually get. Shortcuts are compared
	as raw strings, as everywhere else here - 'Ctrl+Shift+P' and
	'Shift+Ctrl+P' are not recognized as the same.
	"""
	for binding_shortcut, command in parse_bindings(key_bindings):
		if binding_shortcut == shortcut:
			return command
	return None

def binds(key_bindings, shortcut, command):
	"""
	Whether key_bindings already binds `shortcut` to `command`.
	"""
	return (shortcut, command) in parse_bindings(key_bindings)

def key_hint(key_bindings, command, default=''):
	"""
	The user's shortcuts for a viewer pseudo-command, followed by its built-in
	key when that key still runs this command or is unbound.
	"""
	shortcuts = list(get_shortcuts_for_command(key_bindings, command))
	if (
		default and default not in shortcuts
		and command_for_shortcut(key_bindings, default) in (None, command)
	):
		shortcuts.append(default)
	return format_shortcut_hint(shortcuts)

def command_for_key_event(key_event, key_bindings, command_names):
	"""
	First command in command_names whose configured shortcut matches
	key_event, else None. Generalizes core.textviewer_zoom.zoom_delta_for
	(which hardcodes the two pane-font-size commands) to an arbitrary set of
	viewer-only commands, so a viewer can look up "did this keystroke match
	one of my bindable actions?" in one call.
	"""
	for command in command_names:
		for shortcut in get_shortcuts_for_command(key_bindings, command):
			if key_event.matches(shortcut):
				return command
	return None

def dispatch_bindable_command(key_event, key_bindings, commands):
	"""
	Looks up key_event against commands (see command_for_key_event) and, if
	one matches, calls it immediately. Returns whether a command fired, so
	callers can just `if dispatch_bindable_command(...): return` from
	keyPressEvent - shared by all three viewers' keyPressEvent to avoid
	repeating the same lookup-then-call sequence in each.
	"""
	if command_for_key_event(key_event, key_bindings, [DO_NOTHING]) is not None:
		# Explicitly unbound in the user's file: swallow the keystroke instead
		# of letting the viewer's hardcoded fallback keys handle it anyway.
		return True
	command = command_for_key_event(key_event, key_bindings, commands)
	if command is not None:
		commands[command]()
		return True
	return False

def format_shortcut_hint(shortcuts):
	if PLATFORM == 'Mac':
		shortcuts = map(_insert_mac_key_symbols, shortcuts)
	return ', '.join(shortcuts)

def global_command_row(title, command, key_bindings, run):
	# This viewer row follows its current shortcut in the global bindings file.
	return (
		title, run,
		format_shortcut_hint(get_shortcuts_for_command(key_bindings, command)),
		command, KEY_BINDINGS_FILE,
	)

def _insert_mac_key_symbols(shortcut):
	keys = shortcut.split('+')
	return ''.join(_KEY_SYMBOLS_MAC.get(key, key) for key in keys)
