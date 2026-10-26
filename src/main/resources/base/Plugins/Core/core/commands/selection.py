"""Select or deselect files by masks or by the cursor file's extension."""
from core.settings import get_setting, save_setting, SETTINGS_FILE
from fman import DirectoryPaneCommand, QuicksearchItem, show_quicksearch, \
	show_status_message
from fman.fs import is_dir, iterdir
from fman.url import basename, join
from fnmatch import fnmatchcase
from pathlib import PurePath
from dataclasses import dataclass

__all__ = [
	'DeselectGroup', 'DeselectSameExtension', 'SelectGroup',
	'SelectSameExtension'
]

MASK_HISTORY_KEY = 'selection_mask_history'
MASK_HISTORY_LIMIT = 20
ALL_FILES_MASK = '*.*'
_NO_FILE_MESSAGE = 'Put the cursor on a file to use its extension.'


@dataclass(frozen=True)
class SelectionMask:
	includes: tuple[str, ...]
	excludes: tuple[str, ...]

	@classmethod
	def parse(cls, text):
		parts = text.split('|', 1)
		includes = _split_patterns(parts[0])
		excludes = _split_patterns(parts[1]) if len(parts) == 2 else ()
		return cls(includes, excludes)

	def matches(self, name, is_folder):
		if not self.includes and not self.excludes:
			return False
		if any(_matches_pattern(pattern, name, is_folder) for pattern in self.excludes):
			return False
		return not self.includes or any(
			_matches_pattern(pattern, name, is_folder)
			for pattern in self.includes
		)


def _split_patterns(text):
	return tuple(part.strip() for part in text.split(';') if part.strip())


def _matches_pattern(pattern, name, is_folder):
	folder_pattern = pattern.endswith(('\\', '/'))
	if folder_pattern != is_folder:
		return False
	if folder_pattern:
		pattern = pattern[:-1]
	if pattern == ALL_FILES_MASK:
		return not is_folder
	return fnmatchcase(name.lower(), pattern.lower())


def _matching_urls(pane, matches):
	urls = []
	path = pane.get_path()
	for name in iterdir(path):
		url = join(path, name)
		try:
			is_folder = is_dir(url)
			yes = matches(name, is_folder)
		except OSError:
			continue
		if yes:
			urls.append(url)
	return urls


def get_mask_history():
	history = get_setting(SETTINGS_FILE, MASK_HISTORY_KEY, [])
	if not isinstance(history, list):
		return []
	return [mask for mask in history if isinstance(mask, str)]


def remember_mask(mask):
	mask = mask.strip()
	if not mask:
		return
	history = get_mask_history()
	history = [mask] + [item for item in history if item != mask]
	save_setting(
		SETTINGS_FILE, MASK_HISTORY_KEY, history[:MASK_HISTORY_LIMIT]
	)


def _mask_items(query, action_hint='select'):
	history = get_mask_history()
	if query:
		items = [QuicksearchItem(query, hint=action_hint)]
		items.extend(
			QuicksearchItem(mask, hint=action_hint)
			for mask in history
			if query.lower() in mask.lower() and mask != query
		)
	else:
		items = [QuicksearchItem(mask, hint=action_hint) for mask in history]
		if not items:
			items.append(QuicksearchItem(ALL_FILES_MASK, hint=action_hint))
	return items


def _ask_mask(action_hint):
	result = show_quicksearch(
		lambda query: _mask_items(query, action_hint), query=''
	)
	if result is None:
		return None
	query, chosen_value = result
	mask = (chosen_value if chosen_value is not None else query).strip()
	return mask or None


class _GroupCommand(DirectoryPaneCommand):
	def __call__(self, mask=None):
		if mask is None:
			mask = _ask_mask(self._ACTION_HINT)
			if mask is None:
				return
			remember_mask(mask)
		else:
			mask = mask.strip()
		selection_mask = SelectionMask.parse(mask)
		self._apply(_matching_urls(self.pane, selection_mask.matches))
	def _apply(self, urls):
		raise NotImplementedError()


class SelectGroup(_GroupCommand):
	_ACTION_HINT = 'select'
	def _apply(self, urls):
		self.pane.select(urls)


class DeselectGroup(_GroupCommand):
	_ACTION_HINT = 'deselect'
	def _apply(self, urls):
		self.pane.deselect(urls)


class _SameExtensionCommand(DirectoryPaneCommand):
	_ACTION = None
	def __call__(self):
		cursor_file = self.pane.get_file_under_cursor()
		if not cursor_file:
			show_status_message(_NO_FILE_MESSAGE, timeout_secs=3)
			return
		try:
			if is_dir(cursor_file):
				show_status_message(_NO_FILE_MESSAGE, timeout_secs=3)
				return
		except OSError:
			show_status_message(_NO_FILE_MESSAGE, timeout_secs=3)
			return
		suffix = PurePath(basename(cursor_file)).suffix.lower()
		urls = _matching_urls(
			self.pane,
			lambda name, is_folder: not is_folder and
			PurePath(name).suffix.lower() == suffix
		)
		getattr(self.pane, self._ACTION)(urls)


class SelectSameExtension(_SameExtensionCommand):
	_ACTION = 'select'


class DeselectSameExtension(_SameExtensionCommand):
	_ACTION = 'deselect'
