"""Remember the last selected child in each location for folder navigation."""
from urllib.parse import urlsplit, urlunsplit

from core.settings import get_setting, save_setting, SETTINGS_FILE
from fman import (
	ApplicationCommand, DirectoryPaneListener, is_incognito, load_json,
	save_json, show_status_message,
)
from fman.url import basename, dirname, join


HISTORY_FILE = 'Last Visited.json'
SETTING_KEY = 'remember_last_visited'
MAX_ENTRIES = 1000


def is_enabled():
	return get_setting(SETTINGS_FILE, SETTING_KEY, True)


def _history_key(url):
	parsed = urlsplit(url)
	if parsed.scheme == 'file' or '@' not in parsed.netloc:
		return url
	userinfo, separator, host = parsed.netloc.rpartition('@')
	if ':' not in userinfo:
		return url
	username = userinfo.split(':', 1)[0]
	return urlunsplit((
		parsed.scheme, username + separator + host, parsed.path,
		parsed.query, parsed.fragment,
	))


def _history():
	return load_json(HISTORY_FILE, default={}, save_on_quit=True)


def _remember(history, dir_url, child_name):
	key = _history_key(dir_url)
	history.pop(key, None)
	history[key] = child_name
	while len(history) > MAX_ENTRIES:
		del history[next(iter(history))]


def _record_ancestors(history, url):
	child = url
	while True:
		parent = dirname(child)
		if parent == child or parent.endswith('://'):
			return
		_remember(history, parent, basename(child))
		child = parent


class LastVisitedListener(DirectoryPaneListener):
	def before_location_change(self, url, sort_column='', ascending=True):
		if not is_enabled() or is_incognito():
			return None
		cursor = self.pane.get_file_under_cursor()
		if cursor:
			_remember(_history(), self.pane.get_path(), basename(cursor))
		return None

	def on_path_changed(self):
		if not is_enabled():
			return
		history = _history()
		location = self.pane.get_path()
		if not is_incognito():
			_record_ancestors(history, location)
		home = self.pane._get_home_cursor()
		if home is None or self.pane.get_file_under_cursor() != home:
			return
		key = _history_key(location)
		child_name = history.get(key)
		if not child_name or child_name == basename(home):
			return
		try:
			self.pane.place_cursor_at(join(location, child_name))
		except ValueError:
			history.pop(key, None)


class ToggleRememberLastVisited(ApplicationCommand):
	aliases = ('Toggle remember last visited',)

	def __call__(self):
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, SETTING_KEY, enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Remember last visited: ' + state, timeout_secs=3)


class ClearLastVisitedHistory(ApplicationCommand):
	aliases = ('Clear last visited history',)

	def __call__(self):
		_history().clear()
		save_json(HISTORY_FILE)
		show_status_message('Last visited history cleared', timeout_secs=3)


__all__ = [
	'LastVisitedListener', 'ToggleRememberLastVisited',
	'ClearLastVisitedHistory',
]
