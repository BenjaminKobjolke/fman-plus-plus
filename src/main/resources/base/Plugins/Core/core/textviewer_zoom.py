"""
Font-size zoom for the text viewer (core/textviewer.py) - mirrors the pane
font-size feature (core/commands/pane_view.py: increase/decrease/reset pane
font size) but applies to the viewer's own QPlainTextEdit, persisted under
its own settings key so the two zoom levels are independent. Split out of
core/textviewer.py to stay under the project's 300-line file cap.

Deliberately decoupled from PyQt widget styling: callers pass an `apply_size`
callback (new size, or None to clear the override) rather than this module
touching stylesheets itself.
"""
from core.font_size import change_font_size, effective_font_size, \
	get_saved_font_size, reset_font_size, save_font_size
from core.key_bindings import get_shortcuts_for_command, global_command_row
from core.viewer_status import viewer_status

_SETTING_KEY = 'text_viewer_font_size'
# The two global pane font-size commands every viewer's zoom follows (the
# image viewer imports these too), and the viewer-only pseudo-command Reset
# ships (core/textviewer.py binds it).
INCREASE_COMMAND = 'increase_pane_font_size'
DECREASE_COMMAND = 'decrease_pane_font_size'
RESET_COMMAND = 'text_reset_font_size'

def get_saved_view_font_size():
	return get_saved_font_size(_SETTING_KEY)

def save_view_font_size(size):
	save_font_size(_SETTING_KEY, size)

def effective_view_font_size(view):
	return effective_font_size(view.font)

def change_view_font_size(view, apply_size, delta):
	# Reported here rather than from the palette entry so the Alt+Up/Alt+Down
	# key path (zoom_delta_for) confirms the step too.
	viewer_status(
		view._nav.pane,
		'Font size %d'
		% change_font_size(_SETTING_KEY, view.font, apply_size, delta)
	)

def reset_view_font_size(view, apply_size):
	reset_font_size(_SETTING_KEY, apply_size)
	viewer_status(view._nav.pane, 'Font size reset')

def zoom_step(title, command, key_bindings, run):
	"""
	One zoom palette entry (a ViewerAction tuple, see core/viewer_navigation.py)
	for a step that follows the pane font-size shortcut: `run` applies the step,
	`command` is the global command whose current shortcut it follows. Shared
	with the image viewer's own Zoom in/out, which steps a scale rather than a
	font size but hints and rebinds identically.

	The bindings file is the global KEY_BINDINGS_FILE, not the viewer one:
	zoom_delta_for matches against that file, so a Shift+Enter rebind has to
	land there or the viewer would never see it.
	"""
	return global_command_row(title, command, key_bindings, run)

def zoom_actions(view, apply_size, key_bindings):
	"""
	The three ViewerAction tuples the text viewer's palette shows for zoom
	(see core/viewer_navigation.py). Lives here rather than in
	core/textviewer.py both because the labels belong with the zoom they
	drive and because that file is at the 300-line cap. key_bindings is the
	global Key Bindings.json: the two step entries hint at the pane
	font-size shortcut they follow, and Reset ships no key at all.
	"""
	def step(title, delta, command):
		return zoom_step(
			title, command, key_bindings,
			lambda: change_view_font_size(view, apply_size, delta)
		)
	return [
		step('Increase font size', +1, INCREASE_COMMAND),
		step('Decrease font size', -1, DECREASE_COMMAND),
		(
			'Reset font size', lambda: reset_view_font_size(view, apply_size), '',
			RESET_COMMAND,
		),
	]

def zoom_delta_for(key_event, key_bindings):
	"""
	Pure (no Qt event, just a QtKeyEvent + parsed Key Bindings.json): +1/-1 if
	`key_event` matches whatever the user currently has increase/decrease
	pane font size bound to (default Alt+Up/Alt+Down, but this must follow a
	rebind), else None. Reuses the pane font-size feature's own shortcut so
	the viewer doesn't invent a second, separate zoom binding.
	"""
	for command, delta in ((INCREASE_COMMAND, +1), (DECREASE_COMMAND, -1)):
		shortcuts = get_shortcuts_for_command(key_bindings, command)
		if any(key_event.matches(shortcut) for shortcut in shortcuts):
			return delta
	return None
