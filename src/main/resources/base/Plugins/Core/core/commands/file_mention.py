"""The @ file mention popup: fuzzy-find files and folders below this folder.

Like the @ picker of coding agents. The input starts with `@`, the way the
command palette's starts with `>`; deleting it switches to Go To, and typing
`@` in Go To switches here (see core/palette_switch.py). The rows come from
a FileMentionIndex that walks the folder level by level while the popup is
open, so near hits show up first and the list grows as the walk goes on.
"""
from core.commands.util import is_file_url
from core.file_mention_index import FileMentionIndex
from core.palette_switch import FILE_MENTION, GO_TO, MENTION_PREFIX, \
	mention_query_exit, palette_exit_keys, run_palette_switch, \
	strip_mention_prefix
from core.quicksearch_matchers import basename_contains_chars, \
	basename_starts_with, contains_substring, contains_words, matched_in_order
from core.settings import SETTINGS_FILE, get_setting
from fman import DirectoryPaneCommand, QuicksearchExit, QuicksearchItem, \
	show_quicksearch, show_status_message, translate
from fman.localization_keys import FILE_MENTION_LOCAL_ONLY, FILE_MENTION_TITLE
from fman.url import as_human_readable, as_url, dirname

import os

__all__ = ['FileMention']

# The default list ships in Core Settings.json, so it lives in one place.
SETTING_KEY = 'file_mention_excluded'
# Rows are rebuilt per keystroke on the GUI thread; nobody scrolls past this.
RESULT_LIMIT = 200
_MATCHERS = (
	basename_starts_with, contains_substring, contains_words,
	basename_contains_chars
)

class FileMention(DirectoryPaneCommand):
	def __call__(self, query='', continue_typing=False):
		url = self.pane.get_path()
		if not is_file_url(url):
			show_status_message(translate(FILE_MENTION_LOCAL_ONLY), timeout_secs=3)
			return
		shown_query = MENTION_PREFIX + strip_mention_prefix(query)
		index = FileMentionIndex(as_human_readable(url), _excluded_folders())
		index.start()
		try:
			result = show_quicksearch(
				lambda text: suggest_mentions(index.snapshot(), text),
				query=shown_query, title=translate(FILE_MENTION_TITLE),
				set_refresh=index.set_refresh, exit_keys=_exit_keys(),
				query_exit=mention_query_exit,
				select_from=(
					len(shown_query) if continue_typing else len(MENTION_PREFIX)
				)
			)
		finally:
			index.stop()
		if not result:
			return
		if isinstance(result, QuicksearchExit):
			run_palette_switch(self.pane, result)
			return
		entry = result[1]
		if entry is None:
			return
		entry_url = as_url(entry.path)
		if entry.is_dir:
			self.pane.set_path(entry_url)
		else:
			self.pane.set_path(
				dirname(entry_url), lambda: self.pane.place_cursor_at(entry_url)
			)

def suggest_mentions(entries, query):
	"""Rows for `query` over IndexEntry `entries`, best matches first."""
	rows = matched_in_order(
		_MATCHERS, ((entry.rel_path, entry) for entry in entries),
		strip_mention_prefix(query), _make_row
	)
	return rows[:RESULT_LIMIT]

def _make_row(entry, rel_path, highlight):
	# Highlight indices stay valid: replacing os.sep keeps the length.
	title = rel_path.replace(os.sep, '/') + ('/' if entry.is_dir else '')
	return QuicksearchItem(entry, title, highlight=highlight)

def _exit_keys():
	# Only Go To's shortcuts switch away. palette_exit_keys also maps our own
	# shortcut to "close", but that is `@` - closing on it would make `@`
	# impossible to type into the query.
	return {
		key: command
		for key, command in palette_exit_keys(FILE_MENTION, GO_TO).items()
		if command
	}

def _excluded_folders():
	# Read on every open, so edits to the setting apply without a restart.
	names = get_setting(SETTINGS_FILE, SETTING_KEY, ())
	return frozenset(name.lower() for name in names)
