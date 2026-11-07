"""The command palette: fuzzy-search every visible command and run it.

`_suggest_commands` is called per keystroke and buckets its hits by how well
they matched, so exact titles sort above loose keyword hits. The palette
reopens itself after Shift+Enter (editing a command's keywords), which is why
`__call__` is a loop and why the last query and command are remembered.
"""
from core.command_keywords import get_keywords
from core.command_titles import apply_custom_title
from core.key_bindings import get_shortcuts_for_command as \
	_get_shortcuts_for_command, format_shortcut_hint, KEY_BINDINGS_FILE
from core.keyword_editor import edit_command_keywords
from core.palette_switch import COMMAND_PALETTE, GO_TO, palette_exit_keys, \
	run_palette_switch
from core.quicksearch_matchers import bucket_count, contains_chars, \
	contains_chars_after_separator, contains_chars_any_order, \
	match_titles_or_keywords
from fman import DirectoryPaneCommand, get_application_command_aliases, \
	get_application_commands, load_json, QuicksearchItem, \
	run_application_command, show_quicksearch, translate, QuicksearchExit
from fman.localization_keys import COMMAND_PALETTE_TITLE
from itertools import chain

__all__ = ['CommandPalette']

class CommandPalette(DirectoryPaneCommand):

	_MATCHERS = (
		contains_chars_after_separator(' '), contains_chars,
		contains_chars_any_order
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._last_query = ''
		self._last_cmd_name = ''
	def __call__(self, query=None):
		if query is not None:
			self._last_query = query
			self._last_cmd_name = ''
		# A loop, not a single call: editing an entry's keywords (Shift+Enter)
		# reopens the palette where the user left it instead of dropping them
		# back into the panes.
		while True:
			result = show_quicksearch(
				self._suggest_commands, query=self._last_query,
				item=self._get_initial_item(), alt_accept=True,
				title=translate(COMMAND_PALETTE_TITLE),
				exit_keys=palette_exit_keys(COMMAND_PALETTE, GO_TO)
			)
			if not result:
				self._last_query = self._last_cmd_name = ''
				return
			if isinstance(result, QuicksearchExit):
				self._last_query = self._last_cmd_name = ''
				run_palette_switch(self.pane, result)
				return
			query, command, alt = result
			if not command:
				return
			self._last_query = query
			self._last_cmd_name = command.name
			if not alt:
				command()
				return
			edit_command_keywords(command.name, command.title)
	def _get_initial_item(self):
		if not self._last_cmd_name:
			return 0
		initial_suggestions = [
			quicksearch_item.value.name
			for quicksearch_item in self._suggest_commands(self._last_query)
		]
		try:
			return initial_suggestions.index(self._last_cmd_name)
		except ValueError:
			return 0
	def _suggest_commands(self, query):
		# One bucket per matcher, plus the exact-match and loose-keyword
		# ones the helper adds around them - see match_titles_or_keywords.
		result = [[] for _ in range(bucket_count(self._MATCHERS))]
		key_bindings = load_json(KEY_BINDINGS_FILE)
		for cmd_name, aliases, keywords, command in self._get_all_commands():
			match = match_titles_or_keywords(
				self._MATCHERS, [alias.lower() for alias in aliases], keywords,
				query.lower()
			)
			if match is None:
				continue
			bucket, index, highlight = match
			hint = format_shortcut_hint(
				_get_shortcuts_for_command(key_bindings, cmd_name)
			)
			result[bucket].append(
				QuicksearchItem(command, aliases[index], highlight, hint)
			)
		for results in result:
			results.sort(key=lambda item: (len(item.title), item.title))
		return chain.from_iterable(result)
	def _get_all_commands(self):
		result = []
		for cmd_name in self.pane.get_commands():
			if not self.pane.is_command_visible(cmd_name):
				continue
			result.append(_palette_row(
				cmd_name, self.pane.get_command_aliases(cmd_name),
				self.pane.run_command
			))
		for cmd_name in get_application_commands():
			result.append(_palette_row(
				cmd_name, get_application_command_aliases(cmd_name),
				run_application_command
			))
		return result

def _palette_row(cmd_name, aliases, run_fn):
	# The user's rename, if any, replaces the aliases the row is displayed and
	# searched by; the originals live on as keywords - see core/command_titles.
	aliases, keywords = apply_custom_title(
		cmd_name, aliases, get_keywords(cmd_name)
	)
	command = CommandPaletteItem(run_fn, cmd_name, aliases[0])
	return cmd_name, aliases, keywords, command

# _get_shortcuts_for_command / format_shortcut_hint live in core/key_bindings
# (imported above as _get_shortcuts_for_command) so the text viewer's own
# palette can reuse them without a circular import - see that module's
# docstring.

class CommandPaletteItem:
	def __init__(self, run_fn, cmd_name, title):
		self._run_fn = run_fn
		self.name = cmd_name
		# The row's first alias. Kept here because the chosen QuicksearchItem's
		# title is not part of what show_quicksearch returns, and the keyword
		# menus name the command the user picked.
		self.title = title
	def __call__(self):
		self._run_fn(self.name)
