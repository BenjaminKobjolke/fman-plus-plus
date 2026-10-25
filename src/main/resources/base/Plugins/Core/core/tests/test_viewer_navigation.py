from core.tests.viewer_stubs import FakeSettings, StubPane
from core.viewer_navigation import (
	accepts, advance, get_same_type_only, open_viewer_palette, toggle_same_type_only,
	ViewerAction, ViewerNavigator,
)
from unittest import TestCase
from unittest.mock import patch

def _fake_category(url):
	if url.endswith('.png'):
		return 'image'
	if url.endswith('.mp4'):
		return 'video'
	if url.endswith('.txt'):
		return 'text'
	return None

class AdvanceTest(TestCase):
	def setUp(self):
		# Classify by suffix so no real files are touched; _category's own
		# file-sniffing is delegation and not exercised here.
		patcher = patch('core.viewer_navigation._category', _fake_category)
		patcher.start()
		self.addCleanup(patcher.stop)

	def _set_same_type(self, value):
		patcher = patch(
			'core.viewer_navigation.get_same_type_only', lambda category: value
		)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_next_walks_to_immediate_neighbour(self):
		self._set_same_type(False)
		pane = StubPane(['file:///a.png', 'file:///b.png'], cursor=0)
		advance(pane, +1, 'image')
		self.assertEqual('file:///b.png', pane.get_file_under_cursor())
		self.assertEqual(['view_file'], pane.commands)

	def test_previous_walks_backwards(self):
		self._set_same_type(False)
		pane = StubPane(['file:///a.png', 'file:///b.png'], cursor=1)
		advance(pane, -1, 'image')
		self.assertEqual('file:///a.png', pane.get_file_under_cursor())
		self.assertEqual(['view_file'], pane.commands)

	def test_same_type_off_crosses_into_other_category(self):
		self._set_same_type(False)
		pane = StubPane(['file:///a.png', 'file:///b.mp4'], cursor=0)
		advance(pane, +1, 'image')
		self.assertEqual('file:///b.mp4', pane.get_file_under_cursor())
		self.assertEqual(['view_file'], pane.commands)

	def test_same_type_on_skips_differing_category(self):
		self._set_same_type(True)
		pane = StubPane(
			['file:///a.png', 'file:///b.mp4', 'file:///c.png'], cursor=0
		)
		advance(pane, +1, 'image')
		self.assertEqual('file:///c.png', pane.get_file_under_cursor())
		self.assertEqual(['view_file'], pane.commands)

	def test_skips_non_viewable_entries(self):
		self._set_same_type(False)
		# The middle entry classifies as None (a directory / binary).
		pane = StubPane(
			['file:///a.png', 'file:///sub', 'file:///c.txt'], cursor=0
		)
		advance(pane, +1, 'image')
		self.assertEqual('file:///c.txt', pane.get_file_under_cursor())
		self.assertEqual(['view_file'], pane.commands)

	def test_boundary_with_no_match_restores_cursor_and_does_not_view(self):
		self._set_same_type(True)
		pane = StubPane(['file:///a.png', 'file:///b.mp4'], cursor=0)
		advance(pane, +1, 'image')
		self.assertEqual('file:///a.png', pane.get_file_under_cursor())
		self.assertEqual([], pane.commands)
		self.assertEqual([('No further file to view', 3)], pane.status_messages)

	def test_a_successful_step_names_the_file_it_landed_on(self):
		self._set_same_type(True)
		pane = StubPane(['file:///a.png', 'file:///c.png'], cursor=0)
		advance(pane, +1, 'image')
		self.assertEqual(['view_file'], pane.commands)
		self.assertEqual([('c.png', 3)], pane.status_messages)

class AcceptsTest(TestCase):
	def test_viewability_and_same_type(self):
		with patch('core.viewer_navigation._category', _fake_category):
			self.assertFalse(accepts('file:///sub', 'image', False))
			self.assertFalse(accepts('file:///a.mp4', 'image', True))
			self.assertTrue(accepts('file:///a.mp4', 'image', False))
			self.assertTrue(accepts('file:///a.png', 'image', True))

class SameTypePersistenceTest(TestCase):
	def setUp(self):
		self._settings = FakeSettings()
		patcher_get = patch(
			'core.viewer_navigation.get_setting', self._settings.get
		)
		patcher_save = patch(
			'core.viewer_navigation.save_setting', self._settings.save
		)
		patcher_get.start()
		patcher_save.start()
		self.addCleanup(patcher_get.stop)
		self.addCleanup(patcher_save.stop)
		# The settings key is derived from the viewer's name, and validated
		# against the registry so a typo still raises. The registry lives on
		# the running app, which these tests do not have - stand in for it
		# with the three built-in viewers.
		patcher_registry = patch(
			'core.viewers.viewer_for_category',
			lambda name: name if name in ('image', 'video', 'text') else None
		)
		patcher_registry.start()
		self.addCleanup(patcher_registry.stop)

	def test_defaults_to_true_when_nothing_saved(self):
		self.assertIs(True, get_same_type_only('image'))

	def test_toggle_flips_and_persists(self):
		pane = StubPane([])
		self.assertIs(False, toggle_same_type_only(pane, 'image'))
		self.assertIs(False, get_same_type_only('image'))
		self.assertIs(True, toggle_same_type_only(pane, 'image'))
		self.assertIs(True, get_same_type_only('image'))

	def test_toggle_is_per_category(self):
		toggle_same_type_only(StubPane([]), 'image')
		self.assertIs(False, get_same_type_only('image'))
		# Other viewers keep their own default, untouched.
		self.assertIs(True, get_same_type_only('video'))
		self.assertIs(True, get_same_type_only('text'))

	def test_unknown_category_raises(self):
		with self.assertRaises(KeyError):
			get_same_type_only('bogus')

class ViewerNavigatorTest(TestCase):
	def test_exposes_its_pane_read_only(self):
		pane = StubPane([])
		nav = ViewerNavigator(pane=pane, category='image')
		self.assertIs(pane, nav.pane)
		with self.assertRaises(AttributeError):
			nav.pane = StubPane([])

	def test_next_and_previous_delegate_to_advance(self):
		nav = ViewerNavigator(pane='p', category='image')
		with patch('core.viewer_navigation.advance') as adv:
			nav.next_file()
			nav.previous_file()
		self.assertEqual(
			[('p', +1, 'image'), ('p', -1, 'image')],
			[call.args for call in adv.call_args_list],
		)

	def test_same_type_label_reflects_state(self):
		nav = ViewerNavigator(pane='p', category='video')
		with patch('core.viewer_navigation.get_same_type_only', lambda c: True):
			self.assertEqual('Advance across all file types', nav.same_type_label())
		with patch('core.viewer_navigation.get_same_type_only', lambda c: False):
			self.assertEqual('Advance only for same type', nav.same_type_label())

	def test_commands_expose_the_three_bindable_pseudo_commands(self):
		nav = ViewerNavigator(pane='p', category='text')
		commands = nav.commands()
		expected = {
			'viewer_next_file': nav.next_file,
			'viewer_previous_file': nav.previous_file,
			'viewer_toggle_same_type_advance': nav.toggle_same_type,
		}
		self.assertEqual(expected, commands)

class OpenViewerPaletteTest(TestCase):
	def test_runs_the_action_the_picker_returns(self):
		ran = []
		def actions():
			return [('Do it', lambda: ran.append(True), '')]
		# With alt_accept, show_quicksearch returns (query, entry, alt) - the
		# entry being the whole ViewerAction. open_viewer_palette runs its
		# action unless alt says Shift+Enter.
		entry = ViewerAction('Do it', lambda: ran.append(True), '')
		with patch(
			'core.viewer_navigation.show_quicksearch',
			return_value=('', entry, False),
		):
			open_viewer_palette(actions)
		self.assertEqual([True], ran)

	def test_shift_enter_edits_the_entrys_keywords(self):
		ran = []
		entry = ViewerAction(
			'Mute', lambda: ran.append(True), '', 'video_mute'
		)
		# Two results: the Shift+Enter one, then a cancel that ends the loop.
		with patch(
			'core.viewer_navigation.show_quicksearch',
			side_effect=[('', entry, True), None]
		), patch('core.viewer_navigation.edit_command_keywords') as edit:
			open_viewer_palette(lambda: [entry])
		edit.assert_called_once_with(
			'video_mute', 'Mute', 'Viewer Key Bindings.json'
		)
		self.assertEqual([], ran)

	def test_shift_enter_uses_the_entrys_own_bindings_file(self):
		# The zoom entries follow the global pane font-size shortcut, so their
		# rebinds belong in Key Bindings.json - not the viewer file.
		entry = ViewerAction(
			'Increase font size', lambda: None, 'Alt+Up',
			'increase_pane_font_size', 'Key Bindings.json'
		)
		with patch(
			'core.viewer_navigation.show_quicksearch',
			side_effect=[('zoom', entry, True), None]
		), patch('core.viewer_navigation.edit_command_keywords') as edit:
			open_viewer_palette(lambda: [entry])
		edit.assert_called_once_with(
			'increase_pane_font_size', 'Increase font size',
			'Key Bindings.json'
		)

	def test_palette_reopens_on_the_query_that_was_typed(self):
		entry = ViewerAction('Mute', lambda: None, '', 'video_mute')
		with patch(
			'core.viewer_navigation.show_quicksearch',
			side_effect=[('mut', entry, True), None]
		) as quicksearch, patch(
			'core.viewer_navigation.edit_command_keywords'
		):
			open_viewer_palette(lambda: [entry])
		self.assertEqual('', quicksearch.call_args_list[0][1]['query'])
		self.assertEqual('mut', quicksearch.call_args_list[1][1]['query'])

	def test_does_nothing_when_picker_cancelled(self):
		def actions():
			return [('Do it', lambda: None, '')]
		with patch(
			'core.viewer_navigation.show_quicksearch', return_value=None
		):
			open_viewer_palette(actions)  # must not raise

class ViewerPaletteSuggestionsTest(TestCase):

	def test_three_field_entry_still_matches_by_title(self):
		items = self._suggest([('Mute / Unmute', lambda: None, '')], 'mute')
		self.assertEqual(['Mute / Unmute'], [item.title for item in items])
	def test_entry_is_found_by_a_hidden_keyword(self):
		items = self._suggest(
			[('Mute / Unmute', lambda: None, '', 'video_mute')], 'volume',
			keywords={'video_mute': ('volume', 'sound')}
		)
		self.assertEqual(['Mute / Unmute'], [item.title for item in items])
		# Nothing to underline: 'volume' isn't in the title.
		self.assertEqual([], items[0].highlight)
	def test_keyword_of_another_command_does_not_match(self):
		items = self._suggest(
			[('Mute / Unmute', lambda: None, '', 'video_mute')], 'volume',
			keywords={'video_restart': ('volume',)}
		)
		self.assertEqual([], items)

	def test_a_renamed_entry_shows_its_new_name(self):
		items = self._suggest(
			[('Mute / Unmute', lambda: None, '', 'video_mute')], 'silence',
			titles={'video_mute': 'Silence'}
		)
		self.assertEqual(['Silence'], [item.title for item in items])
	def test_a_renamed_entry_is_still_found_by_its_old_name(self):
		items = self._suggest(
			[('Mute / Unmute', lambda: None, '', 'video_mute')], 'mute',
			titles={'video_mute': 'Silence'}
		)
		self.assertEqual(['Silence'], [item.title for item in items])

	def _suggest(self, actions, query, keywords=None, titles=None):
		# open_viewer_palette hands its per-keystroke callback to
		# show_quicksearch; grab it and call it directly.
		captured = []
		titles = titles or {}
		with patch(
			'core.viewer_navigation.show_quicksearch',
			side_effect=lambda get_items, *_, **__: captured.append(get_items)
		), patch(
			'core.viewer_navigation.get_keywords',
			side_effect=lambda name: (keywords or {}).get(name, ())
		), patch(
			'core.command_titles.get_setting',
			side_effect=lambda _json, key, default: titles.get(key, default)
		):
			open_viewer_palette(lambda: actions)
			# Inside the with-block: suggest() looks keywords up when called.
			return list(captured[0](query))
