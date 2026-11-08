"""
The key binding half of the Shift+Enter menus behind a command palette entry:
list the shortcuts a command currently has, add one by pressing it, remove one
again (see docs/KEYBINDINGS.md). The keyword half lives in
core/keyword_editor.py, which is also what opens these screens.

Both binding files are edited the same way - the global 'Key Bindings.json' from
the main palette and 'Viewer Key Bindings.json' from the viewer palettes - so
every screen takes the file to work on. Writes go through core/user_bindings.py,
which reloads the Settings plugin, so a new shortcut works immediately.
"""
from core.key_bindings import binds, command_for_shortcut, DO_NOTHING
from core.quicksearch_screen import QuicksearchScreen
from core.settings_sync_runner import record_settings_change
from core.shortcut_capture import capture_shortcut
from core.user_bindings import (
	load_user_bindings, save_user_bindings, shortcuts_for,
)
from fman import load_json, show_alert, show_status_message, NO, YES

def edit_key_bindings(command_name, title, bindings_file):
	"""
	Open the shortcut list for `command_name`. `title` is the palette row's own
	label, used to name the command in the menus.
	"""
	if not command_name:
		# Same as the keyword editor: viewer entries may ship no command name,
		# and without one there is nothing to bind a key to.
		show_status_message('This entry has no command name to bind a key to.')
		return
	BindingList(command_name, title, bindings_file).show()

class BindingList(QuicksearchScreen):

	_ADD = 'Add shortcut...'

	def __init__(self, command_name, title, bindings_file):
		super().__init__()
		self._command_name = command_name
		self._title = title
		self._bindings_file = bindings_file
		# QuicksearchScreen options are plain strings, so the label a row was
		# picked by has to lead back to the shortcut it stands for.
		self._by_label = {}
	def get_options(self):
		self._by_label = {}
		yield self._ADD
		for shortcut, is_user in shortcuts_for(
			self._bindings_file, self._command_name
		):
			label = '%s  (%s)' % (shortcut, 'yours' if is_user else 'default')
			self._by_label[label] = (shortcut, is_user)
			yield label
	def on_selected(self, option):
		if option == self._ADD:
			self._add()
		else:
			shortcut, is_user = self._by_label[option]
			BindingMenu(
				self._command_name, self._title, shortcut, is_user,
				self._bindings_file
			).show()
	def _add(self):
		shortcut = capture_shortcut('Shortcut for "%s"' % self._title)
		if not shortcut:
			self.show()
			return
		if self._is_taken(shortcut):
			self.show()
			return
		bindings = load_user_bindings(self._bindings_file)
		if not binds(bindings, shortcut, self._command_name):
			# Prepended, not appended: fman prepends each file's bindings as it
			# loads and dispatches first match wins, so the front of the user's
			# file is what beats a shipped default.
			save_user_bindings(self._bindings_file, [
				{'keys': [shortcut], 'command': self._command_name}
			] + bindings)
			record_settings_change(self._bindings_file)
		self.show()
	def _is_taken(self, shortcut):
		occupant = command_for_shortcut(
			load_json(self._bindings_file, default=[]), shortcut
		)
		if occupant is None or occupant == self._command_name:
			return False
		choice = show_alert(
			'%s currently runs %s. Bind it to "%s" instead?'
			% (shortcut, occupant, self._title), YES | NO, YES
		)
		return not choice & YES

class BindingMenu(QuicksearchScreen):

	_REMOVE = 'Remove'
	_GO_BACK = 'Go back'

	def __init__(self, command_name, title, shortcut, is_user, bindings_file):
		super().__init__()
		self._command_name = command_name
		self._title = title
		self._shortcut = shortcut
		self._is_user = is_user
		self._bindings_file = bindings_file
	def get_options(self):
		yield self._REMOVE
		yield self._GO_BACK
	def on_selected(self, option):
		if option == self._REMOVE:
			self._remove()
		self.on_cancelled()
	def on_cancelled(self):
		BindingList(
			self._command_name, self._title, self._bindings_file
		).show()
	def _remove(self):
		bindings = load_user_bindings(self._bindings_file)
		if self._is_user:
			save_user_bindings(self._bindings_file, [
				binding for binding in bindings
				if not binds([binding], self._shortcut, self._command_name)
			])
			record_settings_change(self._bindings_file)
		else:
			# A shipped default cannot be deleted - fman never writes to those
			# files - so it is shadowed by a higher-priority binding that does
			# nothing. See core.key_bindings.DO_NOTHING.
			save_user_bindings(self._bindings_file, [
				{'keys': [self._shortcut], 'command': DO_NOTHING}
			] + bindings)
			record_settings_change(self._bindings_file)
