from core.commands.swap_panes import SwapPanes
from core.tests.commands import FakeWindow
from unittest import TestCase


class _FakeWidget:
	def __init__(self, visible=True):
		self._visible = visible

	def isVisible(self):
		return self._visible

	def setVisible(self, visible):
		self._visible = visible


class _FakePane:
	def __init__(self, window, path, selected=(), cursor=None):
		self.window = window
		self._widget = _FakeWidget()
		self.path = path
		self.selected = list(selected)
		self.cursor = cursor
		self.calls = []

	def get_path(self):
		return self.path

	def get_selected_files(self):
		return list(self.selected)

	def get_file_under_cursor(self):
		return self.cursor

	def set_path(self, path, callback=None):
		self.calls.append(('set_path', path))
		self.path = path
		if callback:
			callback()

	def clear_selection(self):
		self.calls.append(('clear_selection',))
		self.selected = []

	def select(self, urls):
		self.calls.append(('select', list(urls)))
		self.selected.extend(urls)

	def place_cursor_at(self, url):
		self.calls.append(('place_cursor_at', url))
		self.cursor = url

	def focus(self):
		self.calls.append(('focus',))


class SwapPanesTest(TestCase):
	def test_swaps_paths_selection_and_cursor_and_keeps_active_folder_focused(self):
		window = FakeWindow()
		active = _FakePane(
			window, 'file:///left', ['file:///left/one'], 'file:///left/two'
		)
		other = _FakePane(
			window, 'file:///right', ['file:///right/one'], 'file:///right/two'
		)
		window._panes = [active, other]

		SwapPanes(active)()

		self.assertEqual('file:///right', active.path)
		self.assertEqual(['file:///right/one'], active.selected)
		self.assertEqual('file:///right/two', active.cursor)
		self.assertEqual('file:///left', other.path)
		self.assertEqual(['file:///left/one'], other.selected)
		self.assertEqual('file:///left/two', other.cursor)
		self.assertEqual(
			['clear_selection', 'select', 'place_cursor_at'],
			[call[0] for call in active.calls[1:]],
		)
		self.assertEqual(('focus',), other.calls[-1])

	def test_swaps_selection_and_cursor_when_both_panes_show_the_same_folder(self):
		window = FakeWindow()
		active = _FakePane(
			window, 'file:///same', ['file:///same/left'], 'file:///same/a'
		)
		other = _FakePane(
			window, 'file:///same', ['file:///same/right'], 'file:///same/b'
		)
		window._panes = [active, other]

		SwapPanes(active)()

		self.assertEqual(['file:///same/right'], active.selected)
		self.assertEqual('file:///same/b', active.cursor)
		self.assertEqual(['file:///same/left'], other.selected)
		self.assertEqual('file:///same/a', other.cursor)

	def test_does_not_place_cursor_when_a_pane_has_no_file_under_cursor(self):
		window = FakeWindow()
		active = _FakePane(window, 'file:///empty-left')
		other = _FakePane(window, 'file:///empty-right', cursor='file:///right/file')
		window._panes = [active, other]

		SwapPanes(active)()

		self.assertIn('place_cursor_at', [call[0] for call in active.calls])
		self.assertEqual('file:///right/file', active.cursor)
		self.assertNotIn('place_cursor_at', [call[0] for call in other.calls])

	def test_hidden_or_single_pane_is_not_visible_and_call_is_a_noop(self):
		window = FakeWindow()
		active = _FakePane(window, 'file:///left')
		other = _FakePane(window, 'file:///right')
		window._panes = [active, other]
		other._widget.setVisible(False)
		command = SwapPanes(active)

		self.assertFalse(command.is_visible())
		command()
		self.assertEqual([], active.calls)
		self.assertEqual([], other.calls)

		window._panes = [active]
		self.assertFalse(command.is_visible())
		command()
		self.assertEqual([], active.calls)

	def test_swaps_active_pane_with_the_next_pane_when_there_are_three(self):
		window = FakeWindow()
		active = _FakePane(window, 'file:///active', ['file:///active/item'])
		other = _FakePane(window, 'file:///next', ['file:///next/item'])
		third = _FakePane(window, 'file:///third', ['file:///third/item'])
		window._panes = [active, other, third]

		SwapPanes(active)()

		self.assertEqual('file:///next', active.path)
		self.assertEqual(['file:///next/item'], active.selected)
		self.assertEqual('file:///active', other.path)
		self.assertEqual(['file:///active/item'], other.selected)
		self.assertEqual('file:///third', third.path)
		self.assertEqual(['file:///third/item'], third.selected)
		self.assertEqual([], third.calls)
