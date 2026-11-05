"""
The Shift+Enter menus behind a command palette entry: rename it, and view, add
and delete its hidden search keywords (see docs/COMMAND_PALETTE_KEYWORDS.md).
Both the global palette and the viewer palettes hand a command name to
edit_command_keywords; everything below is the menu chain that follows.

The menu also hosts the key binding editor, which lives in
core/binding_editor.py - both palettes reach it the same way, they just hand in
a different bindings file.

Edits go through core.settings, so they land in the user's own
Command Keywords.json / Command Titles.json and take effect on the next
keystroke - no restart.
"""
from core.binding_editor import edit_key_bindings
from core.command_keywords import COMMAND_KEYWORDS_FILE
from core.command_titles import COMMAND_TITLES_FILE, get_custom_title
from core.key_bindings import KEY_BINDINGS_FILE
from core.quicksearch_screen import QuicksearchScreen
from core.settings import get_setting, save_setting
from fman import show_input, show_status_message

def edit_command_keywords(
	command_name, title, bindings_file=KEY_BINDINGS_FILE
):
	"""
	Open the per-entry menu for `command_name`. `title` is the palette row's
	own label, used to name the command in the menus; `bindings_file` is the
	Key Bindings file this palette's commands are bound in.
	"""
	if not command_name:
		# Viewer entries may ship no command name (ViewerAction's default), and
		# without one there is no key to store keywords under.
		show_status_message('This entry has no command name to add keywords to.')
		return
	EntryMenu(command_name, title, bindings_file).show()

def get_editable_keywords(command_name):
	"""
	The keywords of `command_name` as an editable list: the merged shipped +
	user ones, which is also what gets written back - see _save.
	"""
	keywords = get_setting(COMMAND_KEYWORDS_FILE, command_name, [])
	return [
		keyword for keyword in keywords
		if isinstance(keyword, str) and keyword.strip()
	]

def _save(command_name, keywords):
	# The whole merged list, never None: fman's user file replaces its shipped
	# list for a command, and popping a key that a lower-priority file still
	# defines makes the differential write raise ValueError.
	save_setting(COMMAND_KEYWORDS_FILE, command_name, keywords)

class EntryMenu(QuicksearchScreen):

	"""
	What Shift+Enter opens: the per-entry actions, keywords and renaming.
	"""

	_RENAME = 'Rename to...'
	_RESET_NAME = 'Reset name'

	def __init__(self, command_name, title, bindings_file=KEY_BINDINGS_FILE):
		super().__init__()
		self._command_name = command_name
		self._title = title
		self._bindings_file = bindings_file
		self._change_keywords = 'Change keywords for "%s"' % title
		self._change_bindings = 'Change key bindings for "%s"' % title
	def get_options(self):
		yield self._change_keywords
		yield self._change_bindings
		yield self._RENAME
		if get_custom_title(self._command_name):
			yield self._RESET_NAME
	def on_selected(self, option):
		if option == self._change_keywords:
			KeywordList(self._command_name, self._title).show()
		elif option == self._change_bindings:
			edit_key_bindings(
				self._command_name, self._title, self._bindings_file
			)
		elif option == self._RENAME:
			self._rename()
		elif option == self._RESET_NAME:
			# None pops the key: unlike the keywords, no shipped file defines a
			# title, so nothing lower-priority is left for the differential
			# write to trip over.
			save_setting(COMMAND_TITLES_FILE, self._command_name, None)
	def _rename(self):
		title = show_input('New name for "%s":' % self._title)
		if title is None:
			return
		title = title.strip()
		if title:
			save_setting(COMMAND_TITLES_FILE, self._command_name, title)

class KeywordList(QuicksearchScreen):

	_ADD = 'Add keyword...'

	def __init__(self, command_name, title):
		super().__init__()
		self._command_name = command_name
		self._title = title
	def get_options(self):
		yield self._ADD
		yield from get_editable_keywords(self._command_name)
	def on_selected(self, option):
		if option == self._ADD:
			self._add()
		else:
			KeywordMenu(self._command_name, self._title, option).show()
	def _add(self):
		keyword = show_input('New keyword for "%s":' % self._title)
		if keyword is None:
			self.show()
			return
		# Lowercase because that is how keywords are matched - and how the
		# shipped file is checked in tests/test_command_keywords.py.
		keyword = keyword.strip().lower()
		keywords = get_editable_keywords(self._command_name)
		if keyword and keyword not in keywords:
			_save(self._command_name, keywords + [keyword])
		self.show()

class KeywordMenu(QuicksearchScreen):

	_DELETE = 'Delete'
	_GO_BACK = 'Go back'

	def __init__(self, command_name, title, keyword):
		super().__init__()
		self._command_name = command_name
		self._title = title
		self._keyword = keyword
	def get_options(self):
		yield self._DELETE
		yield self._GO_BACK
	def on_selected(self, option):
		if option == self._DELETE:
			_save(self._command_name, [
				keyword for keyword in get_editable_keywords(self._command_name)
				if keyword != self._keyword
			])
		self.on_cancelled()
	def on_cancelled(self):
		KeywordList(self._command_name, self._title).show()
