"""
The two stand-ins every viewer test needs: a DirectoryPane with a cursor, and
the Core Settings.json get/save pair.

Not named test_*.py on purpose - tools/run_core_tests.bat discovers by that
pattern, and this module defines no tests. It exists because StubPane in
particular encodes a contract (Qt's moveCursor clamps at both ends, it does
not wrap) that core/viewer_navigation.py's advance() and
core/viewer_file_ops.py's delete_current() both rely on; a copy per test file
drifts from that the moment either changes.
"""

class StubPane:
	"""
	Minimal stand-in for a DirectoryPane: a fixed url list plus a cursor that
	clamps at both ends, exactly like Qt's moveCursor (see
	fman/impl/view/cursor_movement.py). run_command just records the call so
	tests can assert view_file was (or wasn't) re-run.
	"""
	def __init__(self, urls, cursor=0, aliases=None, viewer_commands=(), on_run=None):
		self._urls = urls
		self._cursor = cursor
		self.commands = []
		self.selected = []
		self.selection_during_command = []
		self._aliases = aliases or {}
		self._viewer_commands = set(viewer_commands)
		self.on_run = on_run
		self.status_messages = []

	def show_status_message(self, text, timeout_secs=None):
		self.status_messages.append((text, timeout_secs))

	def get_selected_files(self):
		return list(self.selected)

	def clear_selection(self):
		self.selected.clear()

	def select(self, urls):
		self.selected.extend(urls)

	def get_viewer_commands(self):
		return self._viewer_commands

	def _rewrite_command(self, name, args):
		return name, args

	def get_command_aliases(self, name):
		return (self._aliases[name],)

	def is_command_visible(self, name):
		return name in self._aliases

	def get_file_under_cursor(self):
		if 0 <= self._cursor < len(self._urls):
			return self._urls[self._cursor]
		return None

	def move_cursor_down(self):
		if self._cursor < len(self._urls) - 1:
			self._cursor += 1

	def move_cursor_up(self):
		if self._cursor > 0:
			self._cursor -= 1

	def place_cursor_at(self, url):
		self._cursor = self._urls.index(url)

	def run_command(self, name):
		self.commands.append(name)
		self.selection_during_command.append(list(self.selected))
		if self.on_run:
			self.on_run(name)

class FakeSettings:
	"""
	Stands in for core/settings.py's get_setting/save_setting, which are
	untested elsewhere and would otherwise write to the real settings file.
	Patch the pair where the module under test imported them.
	"""
	def __init__(self):
		self._values = {}

	def get(self, json_name, key, default=None):
		return self._values.get(key, default)

	def save(self, json_name, key, value):
		if value is None:
			self._values.pop(key, None)
		else:
			self._values[key] = value
