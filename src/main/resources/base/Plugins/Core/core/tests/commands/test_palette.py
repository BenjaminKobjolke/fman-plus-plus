from core.commands.palette import CommandPalette
from fman.localization_keys import COMMAND_PALETTE_TITLE
from unittest import TestCase
from unittest.mock import Mock, patch

class CommandPaletteSuggestionsTest(TestCase):

	"""
	The palette's per-keystroke callback: what it offers, and under which
	title. A keyword hit must keep the command's own name on the row - showing
	the matched synonym instead is exactly what made 'transparency' confusing.
	"""

	class _StubPane:
		def __init__(self, aliases_by_command):
			self._aliases = aliases_by_command
		def get_commands(self):
			return list(self._aliases)
		def is_command_visible(self, _command_name):
			return True
		def get_command_aliases(self, command_name):
			return self._aliases[command_name]
		def run_command(self, _command_name):
			pass

	def test_command_is_found_by_its_name(self):
		items = self._suggest('opacity')
		self.assertEqual(['Set window opacity'], [i.title for i in items])
		self.assertTrue(items[0].highlight)
	def test_command_is_found_by_a_hidden_keyword(self):
		items = self._suggest('transparency')
		self.assertEqual(['Set window opacity'], [i.title for i in items])
		self.assertEqual([], items[0].highlight)
	def test_equally_exact_matches_sort_by_title(self):
		# 'reload' is both Reload's name and a keyword of set_window_opacity
		# in this fixture, so both match exactly and share the top rank. The
		# shorter title then goes first.
		titles = [item.title for item in self._suggest('reload')]
		self.assertEqual(['Reload', 'Set window opacity'], titles)
	def test_exact_keyword_ranks_above_a_loose_name_match(self):
		# The bug this ordering fixes: 'exit' is a mid-word subsequence of
		# 'Extract to opposite', but the whole of Quit's hidden keyword.
		titles = [item.title for item in self._suggest('exit')]
		self.assertEqual(['Quit', 'Extract to opposite'], titles)
	def test_unknown_query_matches_nothing(self):
		self.assertEqual([], self._suggest('zzz'))
	def test_command_prefix_does_not_change_matching(self):
		self.assertEqual(
			[self._item_signature(item) for item in self._suggest('copy')],
			[self._item_signature(item) for item in self._suggest('>copy')]
		)
	def test_a_renamed_command_shows_its_new_name(self):
		items = self._suggest('bye', titles={'quit': 'Bye'})
		self.assertEqual(['Bye'], [i.title for i in items])
	def test_a_renamed_command_is_still_found_by_its_old_name(self):
		items = self._suggest('quit', titles={'quit': 'Bye'})
		# Found as a keyword now, so the row shows the new name and
		# underlines nothing.
		self.assertEqual(['Bye'], [i.title for i in items])
		self.assertEqual([], items[0].highlight)

	def _suggest(self, query, titles=None):
		keywords = {
			'set_window_opacity': ('transparency', 'reload'),
			'reload': (),
			'quit': ('exit', 'copy'),
			'extract_to_opposite': (),
		}
		pane = self._StubPane({
			'set_window_opacity': ('Set window opacity',),
			'reload': ('Reload',),
			'quit': ('Quit',),
			'extract_to_opposite': ('Extract to opposite',),
		})
		titles = titles or {}
		with patch('core.commands.palette.load_json', return_value=[]), \
			patch(
				'core.commands.palette.get_application_commands',
				return_value=[]
			), patch(
				'core.commands.palette.get_keywords',
				side_effect=lambda name: keywords.get(name, ())
			), patch(
				'core.command_titles.get_setting',
				side_effect=lambda _json, key, default: titles.get(key, default)
			):
			return list(CommandPalette(pane)._suggest_commands(query))
	def _item_signature(self, item):
		return item.value.name, item.title, item.highlight


class CommandPaletteTitleTest(TestCase):
	def test_passes_translated_title_to_quicksearch(self):
		with patch(
			'core.commands.palette.translate', return_value='translated title'
		) as translate, patch(
			'core.commands.palette.show_quicksearch', return_value=None
		) as show:
			CommandPalette(Mock())()

		translate.assert_called_once_with(COMMAND_PALETTE_TITLE)
		self.assertEqual(
			'translated title', show.call_args.kwargs['title']
		)
	def test_shows_prefix_with_query_selected_after_it_by_default(self):
		with patch(
			'core.commands.palette.show_quicksearch', return_value=None
		) as show:
			CommandPalette(Mock())()

		self.assertEqual('>', show.call_args.kwargs['query'])
		self.assertEqual(1, show.call_args.kwargs['select_from'])
	def test_text_switch_shows_query_and_places_cursor_at_end(self):
		with patch(
			'core.commands.palette.show_quicksearch', return_value=None
		) as show:
			CommandPalette(Mock())(query='abc', continue_typing=True)

		self.assertEqual('>abc', show.call_args.kwargs['query'])
		self.assertEqual(4, show.call_args.kwargs['select_from'])
