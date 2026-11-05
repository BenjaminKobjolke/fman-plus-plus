from core.textviewer_search import (
	find_index, key_hint, search_status, ViewerSearch,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from unittest import TestCase
from unittest.mock import patch

class FindIndexTest(TestCase):
	_TEXT = 'one two three two one'

	def test_finds_first_match_from_start(self):
		self.assertEqual((4, False), find_index(self._TEXT, 'two', 0))

	def test_from_pos_skips_earlier_matches(self):
		self.assertEqual((14, False), find_index(self._TEXT, 'two', 7))

	def test_is_case_insensitive(self):
		self.assertEqual((4, False), find_index('one TWO', 'two', 0))
		self.assertEqual((4, False), find_index('one two', 'TWO', 0))

	def test_wraps_forward_past_the_last_match(self):
		self.assertEqual((4, True), find_index(self._TEXT, 'two', 18))

	def test_backward_finds_the_previous_match(self):
		self.assertEqual((4, False), find_index(self._TEXT, 'two', 14, True))

	def test_wraps_backward_before_the_first_match(self):
		self.assertEqual((14, True), find_index(self._TEXT, 'two', 2, True))

	def test_no_match_returns_none(self):
		self.assertIsNone(find_index(self._TEXT, 'four', 0))
		self.assertIsNone(find_index(self._TEXT, 'four', 0, True))

	def test_empty_query_returns_none(self):
		self.assertIsNone(find_index(self._TEXT, '', 0))

class KeyHintTest(TestCase):
	def test_falls_back_to_the_hardcoded_default_when_unbound(self):
		self.assertEqual('/', key_hint([], 'text_find', '/'))

	def test_follows_a_rebind(self):
		bindings = [{'keys': ['Ctrl+F'], 'command': 'text_find'}]
		self.assertEqual('Ctrl+F', key_hint(bindings, 'text_find', '/'))

class SearchStatusTest(TestCase):
	def test_names_the_query_and_every_key(self):
		hints = {
			'text_find': '/', 'text_find_next': 'n',
			'text_find_previous': 'N', 'text_search_exit': 'Esc'
		}
		self.assertEqual(
			'Search: needle  (n next, N previous, Esc exit)',
			search_status('needle', hints)
		)

class _FakeCursor:
	def __init__(self, start=0, end=0):
		self._start = start
		self._end = end
		self.positions = []

	def selectionStart(self):
		return self._start

	def selectionEnd(self):
		return self._end

	def setPosition(self, position, mode=None):
		self.positions.append((position, mode))

class _FakeView:
	# Stand-in for PaneTextView: ViewerSearch only ever reads its text and
	# moves its cursor, so no QApplication (and no real widget) is needed.
	def __init__(self, text, cursor=None):
		self._text = text
		self._cursor = cursor or _FakeCursor()
		self.selected = []

	def toPlainText(self):
		return self._text

	def textCursor(self):
		return self._cursor

	def setTextCursor(self, cursor):
		self.selected.append(cursor)

class _FakeKeyEvent:
	def __init__(self, key, modifiers=Qt.NoModifier):
		self._key = key
		self._modifiers = modifiers

	def key(self):
		return self._key

	def modifiers(self):
		return self._modifiers

class ViewerSearchTest(TestCase):
	def setUp(self):
		self.messages = []
		self.prompts = ['two']
		patches = {
			'load_json': lambda *_args, **_kwargs: [],
			'show_input': lambda *_args, **_kwargs: self.prompts.pop(0),
			'show_status_message': self.messages.append,
			'clear_status_message': lambda: self.messages.append(None),
		}
		for name, replacement in patches.items():
			patcher = patch('core.textviewer_search.' + name, replacement)
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_start_selects_the_first_match_and_says_so(self):
		view = _FakeView('one two three two one')
		search = ViewerSearch(view)
		search.start()
		self.assertEqual(
			[(4, None), (7, QTextCursor.KeepAnchor)],
			view.textCursor().positions
		)
		self.assertEqual(1, len(view.selected))
		self.assertEqual(
			['Search: two  (n next, N previous, Esc exit)'], self.messages
		)

	def test_find_advances_from_the_current_selection(self):
		cursor = _FakeCursor(4, 7)
		view = _FakeView('one two three two one', cursor)
		search = ViewerSearch(view)
		search.start()
		cursor.positions.clear()
		search.find()
		self.assertEqual(
			[(14, None), (17, QTextCursor.KeepAnchor)], cursor.positions
		)

	def test_find_backwards_wraps_and_says_so(self):
		view = _FakeView('one two three two one')
		search = ViewerSearch(view)
		search.start()
		search.find(backward=True)
		self.assertEqual(
			'Search: two  (n next, N previous, Esc exit)  (wrapped)',
			self.messages[-1]
		)

	def test_no_match_leaves_the_cursor_alone(self):
		self.prompts = ['zzz']
		view = _FakeView('one two three')
		search = ViewerSearch(view)
		search.start()
		self.assertEqual([], view.selected)
		self.assertEqual(['No match: zzz'], self.messages)

	def test_cancelled_prompt_does_nothing(self):
		self.prompts = [None]
		view = _FakeView('one two three')
		search = ViewerSearch(view)
		search.start()
		self.assertEqual([], view.selected)
		self.assertEqual([], self.messages)
		self.assertEqual([], search.actions()[3:])

	def test_slash_starts_a_search_and_n_walks_it(self):
		view = _FakeView('one two three two one')
		search = ViewerSearch(view)
		self.assertTrue(search.handle_key(_FakeKeyEvent(Qt.Key_Slash)))
		self.assertTrue(search.handle_key(_FakeKeyEvent(Qt.Key_N)))
		self.assertTrue(
			search.handle_key(_FakeKeyEvent(Qt.Key_N, Qt.ShiftModifier))
		)
		self.assertEqual(3, len(view.selected))

	def test_n_is_ignored_until_there_is_a_query(self):
		search = ViewerSearch(_FakeView('one two'))
		self.assertFalse(search.handle_key(_FakeKeyEvent(Qt.Key_N)))

	def test_escape_only_consumed_while_searching(self):
		search = ViewerSearch(_FakeView('one two three'))
		escape = _FakeKeyEvent(Qt.Key_Escape)
		# Not searching: the viewer's own close handling must still see it.
		self.assertFalse(search.handle_key(escape))
		search.start()
		self.assertTrue(search.handle_key(escape))
		self.assertIsNone(self.messages[-1])
		self.assertFalse(search.handle_key(escape))

	def test_exit_entry_only_appears_while_searching(self):
		search = ViewerSearch(_FakeView('one two three'))
		self.assertEqual(
			['Find…', 'Find next', 'Find previous'],
			[title for title, _action, _hint, _name in search.actions()]
		)
		search.start()
		self.assertEqual(
			[
				('Find…', '/', 'text_find'),
				('Find next', 'n', 'text_find_next'),
				('Find previous', 'N', 'text_find_previous'),
				('Exit search mode', 'Esc', 'text_search_exit'),
			],
			[
				(title, hint, name)
				for title, _action, hint, name in search.actions()
			]
		)

	def test_every_palette_entry_is_bindable_under_the_same_name(self):
		# A palette entry whose command name has no binding counterpart would
		# be unbindable, and a bound key with no entry undiscoverable.
		search = ViewerSearch(_FakeView('one two three'))
		search.start()
		self.assertEqual(
			set(search.commands()),
			{name for _title, _action, _hint, name in search.actions()}
		)
