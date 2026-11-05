"""
Vim-style find inside the text viewer: "/" prompts for a query, n/N walk the
matches, Esc leaves search mode again (a second Esc closes the viewer, as
before). Injected into PaneTextView as a collaborator - the same shape
core/viewer_navigation.py's ViewerNavigator uses for next/previous-file -
partly so core/textviewer.py stays under the project's 300-line file cap, and
partly because none of this is the widget's own concern.

Matching is case-insensitive and wraps once at either end. The match is
selected rather than painted, so Qt scrolls it into view for free and the
theme's own selection colors apply.
"""
from core.key_bindings import (
	format_shortcut_hint, get_shortcuts_for_command, VIEWER_KEY_BINDINGS_FILE,
)
from fman import (
	clear_status_message, load_json, show_input, show_status_message,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor

# One row per viewer pseudo-command: its name, the key this viewer hardcodes
# for it (see handle_key), which doubles as the palette hint shown when the
# user has bound nothing of their own, and its palette title. Listed in the
# order the palette shows them.
COMMANDS = (
	('text_find', '/', 'Find…'),
	('text_find_next', 'n', 'Find next'),
	('text_find_previous', 'N', 'Find previous'),
	('text_search_exit', 'Esc', 'Exit search mode'),
)

def find_index(text, query, from_pos, backward=False):
	"""
	(index, wrapped) of the next case-insensitive occurrence of query, or None
	if text holds none at all. The search wraps once around the end of the text
	(or its start, when backward); wrapped says whether it had to.
	"""
	if not query:
		return None
	haystack = text.lower()
	needle = query.lower()
	from_pos = max(from_pos, 0)
	# The wrapped scan only runs when the first one came up empty, so a normal
	# hit never pays for a second pass over the (up to 2 MB) buffer.
	if backward:
		found = haystack.rfind(needle, 0, from_pos)
		if found != -1:
			return found, False
		found = haystack.rfind(needle)
	else:
		found = haystack.find(needle, from_pos)
		if found != -1:
			return found, False
		found = haystack.find(needle)
	if found == -1:
		return None
	return found, True

def key_hint(key_bindings, command, default):
	"""
	The key the user has bound to a viewer pseudo-command, else the default
	this viewer hardcodes for it - so the palette hint follows a rebind.
	"""
	return format_shortcut_hint(
		get_shortcuts_for_command(key_bindings, command)
	) or default

def search_status(query, hints):
	# The persistent status-bar line that says search mode is on, naming the
	# keys that actually walk/leave it (hints: command name -> key).
	return 'Search: %s  (%s next, %s previous, %s exit)' % (
		query, hints['text_find_next'], hints['text_find_previous'],
		hints['text_search_exit']
	)

def _hints():
	key_bindings = load_json(VIEWER_KEY_BINDINGS_FILE, default=[])
	return {
		command: key_hint(key_bindings, command, default)
		for command, default, _title in COMMANDS
	}

class ViewerSearch:
	"""
	Per-view search collaborator, bound to one PaneTextView. Holds the last
	query and whether search mode is currently on - the latter only so Esc
	knows whether to leave search mode or fall through to closing the viewer,
	and so "Exit search mode" only appears in the palette when there is
	something to exit.
	"""
	def __init__(self, view):
		self._view = view
		self._query = ''
		self._active = False

	def start(self):
		# Modal, like "Save file as…" - fman's API has no non-modal input.
		# Pre-filled with the last query so repeating a search is / + Enter.
		query = show_input('/', default=self._query)
		if not query:
			return
		self._query = query
		self._active = True
		# From selectionStart, not the cursor's end: a query typed while an
		# earlier match is selected should match that spot again rather than
		# skipping to the next one.
		self._jump(self._view.textCursor().selectionStart())

	def find(self, backward=False):
		if not self._query:
			self.start()
			return
		self._active = True
		cursor = self._view.textCursor()
		self._jump(
			cursor.selectionStart() if backward else cursor.selectionEnd(),
			backward
		)

	def _jump(self, from_pos, backward=False):
		match = find_index(
			self._view.toPlainText(), self._query, from_pos, backward
		)
		if match is None:
			# Cursor left where it was: a typo shouldn't lose your place.
			show_status_message('No match: %s' % self._query)
			return
		index, wrapped = match
		cursor = self._view.textCursor()
		cursor.setPosition(index)
		cursor.setPosition(index + len(self._query), QTextCursor.KeepAnchor)
		# Selecting rather than painting the match: Qt scrolls it into view
		# for free, in the theme's own selection colors.
		self._view.setTextCursor(cursor)
		status = search_status(self._query, _hints())
		show_status_message((status + '  (wrapped)') if wrapped else status)

	def exit(self):
		if not self._active:
			return
		self._active = False
		clear_status_message()

	def handle_key(self, event):
		"""
		This viewer's hardcoded view-mode defaults, checked after the user's
		own Viewer Key Bindings.json (see PaneTextView.keyPressEvent, where a
		rebind therefore wins). Returns whether the key was consumed - an Esc
		with search mode off is not, so it still closes the viewer.
		"""
		key = event.key()
		if key == Qt.Key_Slash:
			self.start()
			return True
		if key == Qt.Key_N and self._query:
			self.find(backward=bool(event.modifiers() & Qt.ShiftModifier))
			return True
		if key == Qt.Key_Escape and self._active:
			self.exit()
			return True
		return False

	def actions(self):
		# ViewerAction tuples for the viewer palette (see
		# core/viewer_navigation.py). Hints come from the viewer's own bindings
		# file, not the global one the zoom entries use.
		hints = _hints()
		commands = self.commands()
		return [
			(title, commands[name], hints[name], name)
			for name, _default, title in COMMANDS
			if self._active or name != 'text_search_exit'
		]

	def commands(self):
		# The bindable-pseudo-command mappings PaneTextView merges into its own
		# _bindable_commands() dict; also the single source of the callables
		# actions() puts behind the palette entries.
		return {
			'text_find': self.start,
			'text_find_next': self.find,
			'text_find_previous': lambda: self.find(backward=True),
			'text_search_exit': self.exit,
		}
