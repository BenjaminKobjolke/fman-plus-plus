"""Commands for pinning local folders to the Windows taskbar jump list."""
import os

from core.commands.util import is_file_url
from core.quicksearch_matchers import contains_substring
from core.taskbar_jump_list import (
	_normalized_path, get_pinned_folders, rebuild, save_pinned_folders,
)
from fman import DirectoryPaneCommand, DirectoryPaneListener, QuicksearchItem, \
	PLATFORM, show_quicksearch, show_status_message
from fman.url import as_human_readable


__all__ = [
	'PinFolderToTaskbar', 'TaskbarJumpListListener', 'UnpinFolderFromTaskbar'
]

_LISTENER_REBUILT = False


def _matching_items(paths, query):
	terms = query.lower().split()
	for path in paths:
		lower_path = path.lower()
		highlights = set()
		for term in terms:
			match = contains_substring(lower_path, term)
			if match is None:
				break
			highlights.update(match)
		else:
			name = os.path.basename(path.rstrip('\\/')) or path
			yield QuicksearchItem(
				path, name, sorted(highlights), description=path
			)


def _save_rebuilt_paths(paths):
	rebuilt_paths = rebuild(paths)
	if rebuilt_paths != paths:
		save_pinned_folders(rebuilt_paths)
	return rebuilt_paths


class PinFolderToTaskbar(DirectoryPaneCommand):
	aliases = ('Pin folder to taskbar',)

	def is_visible(self):
		return PLATFORM == 'Windows' and is_file_url(self.pane.get_path())

	def __call__(self):
		path = as_human_readable(self.pane.get_path())
		paths = get_pinned_folders()
		if any(_normalized_path(path) == _normalized_path(pinned)
				for pinned in paths):
			name = os.path.basename(path.rstrip('\\/')) or path
			show_status_message('Already pinned to taskbar: ' + name)
			return
		paths.append(path)
		save_pinned_folders(paths)
		_save_rebuilt_paths(paths)
		name = os.path.basename(path.rstrip('\\/')) or path
		show_status_message('Pinned to taskbar: ' + name)


class UnpinFolderFromTaskbar(DirectoryPaneCommand):
	aliases = ('Unpin folder from taskbar',)

	def is_visible(self):
		return PLATFORM == 'Windows' and bool(get_pinned_folders())

	def __call__(self):
		paths = get_pinned_folders()
		if not paths:
			return
		result = show_quicksearch(
			lambda query: _matching_items(paths, query)
		)
		if not result or result[1] is None:
			return
		selected_path = result[1]
		remaining = [
			path for path in paths
			if _normalized_path(path) != _normalized_path(selected_path)
		]
		save_pinned_folders(remaining)
		_save_rebuilt_paths(remaining)
		name = os.path.basename(selected_path.rstrip('\\/')) or selected_path
		show_status_message('Unpinned from taskbar: ' + name)


class TaskbarJumpListListener(DirectoryPaneListener):
	def on_path_changed(self):
		global _LISTENER_REBUILT
		if _LISTENER_REBUILT or PLATFORM != 'Windows':
			return
		_LISTENER_REBUILT = True
		paths = get_pinned_folders()
		if paths:
			_save_rebuilt_paths(paths)
