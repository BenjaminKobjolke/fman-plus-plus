"""
The text viewer's four cursor keys - Home/End jump to the top/bottom of the
file and PgUp/PgDown page - as viewer pseudo-commands, so they show up in the
viewer's palette and can be rebound like every other one. Injected into
PaneTextView as a collaborator, the same shape core/textviewer_search.py's
ViewerSearch uses (and for the same reason: core/textviewer.py has to stay
under the project's 300-line file cap).

The hardcoded defaults below only fire in view mode, like search's "/" and
n/N: while editing, Home/End have to keep Qt's line-start/line-end editing
semantics. The commands themselves stay bindable in both modes, so a user who
wants them while typing can bind e.g. Ctrl+Home to text_go_to_top.

Paging hands a synthesized key event to the base QPlainTextEdit rather than
moving the cursor itself: QTextCursor has no page-move operation, so Qt's own
paging is only reachable through that method.
"""
from core.key_bindings import VIEWER_KEY_BINDINGS_FILE, key_hint
from core.textviewer_reload import scroll_to_end
from fman import load_json
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeyEvent, QTextCursor
from PyQt5.QtWidgets import QPlainTextEdit

def _page(view, key):
	QPlainTextEdit.keyPressEvent(
		view, QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
	)

# One row per viewer pseudo-command: its name, the key this viewer hardcodes
# for it (which doubles as the palette hint when the user has bound nothing of
# their own), its palette title, and what it does to the view. Listed in the
# order the palette shows them.
COMMANDS = (
	(
		'text_go_to_top', 'Home', 'Go to top',
		lambda view: view.moveCursor(QTextCursor.Start)
	),
	('text_go_to_bottom', 'End', 'Go to bottom', scroll_to_end),
	('text_page_up', 'PgUp', 'Page up', lambda view: _page(view, Qt.Key_PageUp)),
	(
		'text_page_down', 'PgDown', 'Page down',
		lambda view: _page(view, Qt.Key_PageDown)
	),
)

class ViewerCursor:
	"""
	Per-view cursor-key collaborator, bound to one PaneTextView. Stateless -
	unlike ViewerSearch there is nothing to remember between keystrokes.
	"""
	def __init__(self, view):
		self._view = view

	def handle_key(self, key_event):
		"""
		This viewer's hardcoded view-mode defaults, checked after the user's
		own Viewer Key Bindings.json (see PaneTextView.keyPressEvent, where a
		rebind therefore wins). Takes the QtKeyEvent that method already
		built, so matching goes through fman's own shortcut matcher and the
		table above can stay plain strings that double as palette hints.
		Matching is exact, so Shift+Home, Ctrl+Home and Num+Home keep falling
		through to Qt's own selection/document-jump handling.
		"""
		commands = self.commands()
		for name, default, _title, _action in COMMANDS:
			if key_event.matches(default):
				commands[name]()
				return True
		return False

	def actions(self):
		# ViewerAction tuples for the viewer palette (see
		# core/viewer_navigation.py). Hints come from the viewer's own
		# bindings file, like the search entries' do.
		key_bindings = load_json(VIEWER_KEY_BINDINGS_FILE, default=[])
		commands = self.commands()
		return [
			(title, commands[name], key_hint(key_bindings, name, default), name)
			for name, default, title, _action in COMMANDS
		]

	def commands(self):
		# The bindable-pseudo-command mappings PaneTextView merges into its
		# own _bindable_commands() dict; also the single source of the
		# callables actions() puts behind the palette entries.
		return {
			name: (lambda action=action: action(self._view))
			for name, _default, _title, action in COMMANDS
		}
