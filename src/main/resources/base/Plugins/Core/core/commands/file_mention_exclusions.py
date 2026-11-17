"""Commands for managing folders skipped by the @ file mention search."""
import os

from core.commands.file_mention import SETTING_KEY
from core.quicksearch_matchers import contains_substring
from core.settings import SETTINGS_FILE, get_setting, save_setting
from fman import (
	DirectoryPaneCommand, QuicksearchItem, show_prompt, show_quicksearch,
	show_status_message,
)
import fman.fs

__all__ = [
	'ExcludeFolderFromFileMention', 'IncludeFolderInFileMention',
]


def get_excluded_names():
	return list(get_setting(SETTINGS_FILE, SETTING_KEY, []))


def _matching_items(names, query):
	terms = query.lower().split()
	for name in names:
		lower_name = name.lower()
		highlights = set()
		for term in terms:
			match = contains_substring(lower_name, term)
			if match is None:
				break
			highlights.update(match)
		else:
			yield QuicksearchItem(name, name, sorted(highlights))


class ExcludeFolderFromFileMention(DirectoryPaneCommand):
	aliases = ('Exclude folder from @ file search',)

	def __call__(self):
		file_under_cursor = self.pane.get_file_under_cursor()
		default_name = ''
		if file_under_cursor and fman.fs.is_dir(file_under_cursor):
			default_name = os.path.basename(file_under_cursor.rstrip('\\/'))
		name = show_prompt(
			'Folder name to skip in @ file search:', default=default_name
		)
		if not name or not name.strip():
			return
		name = name.strip()
		if '/' in name or '\\' in name:
			show_status_message('Folder names cannot contain / or \\')
			return
		names = get_excluded_names()
		if any(existing.lower() == name.lower() for existing in names):
			show_status_message('Already excluded: ' + name)
			return
		names.append(name)
		save_setting(SETTINGS_FILE, SETTING_KEY, names)
		show_status_message('Excluded from @ file search: ' + name)


class IncludeFolderInFileMention(DirectoryPaneCommand):
	aliases = ('Remove folder from @ file search exclusions',)

	def is_visible(self):
		return bool(get_excluded_names())

	def __call__(self):
		names = get_excluded_names()
		if not names:
			return
		result = show_quicksearch(
			lambda query: _matching_items(names, query)
		)
		if not result or result[1] is None:
			return
		selected_name = result[1]
		names.remove(selected_name)
		save_setting(SETTINGS_FILE, SETTING_KEY, names)
		show_status_message(
			'Removed from @ file search exclusions: ' + selected_name
		)
