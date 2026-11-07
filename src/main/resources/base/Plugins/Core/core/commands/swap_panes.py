"""Swap pane locations for upstream #318 (Ctrl+U in MC and TC).

Read both panes' state before either location change starts: directory loads
may be asynchronous, and otherwise one callback could observe half-swapped
state from the other pane.
"""
from core.commands.pane_view import _any_pane_hidden
from core.commands.util import get_opposite_pane
from fman import DirectoryPaneCommand

__all__ = ['SwapPanes']


class SwapPanes(DirectoryPaneCommand):
	def is_visible(self):
		return _can_swap(self.pane.window.get_panes())

	def __call__(self):
		panes = self.pane.window.get_panes()
		if not _can_swap(panes):
			return

		other = get_opposite_pane(self.pane)
		own_path = self.pane.get_path()
		own_selection = self.pane.get_selected_files()
		own_cursor = self.pane.get_file_under_cursor()
		other_path = other.get_path()
		other_selection = other.get_selected_files()
		other_cursor = other.get_file_under_cursor()

		other.set_path(
			own_path,
			callback=lambda: _restore(
				other, own_selection, own_cursor
			)
		)
		self.pane.set_path(
			other_path,
			callback=lambda: _restore(
				self.pane, other_selection, other_cursor
			)
		)
		other.focus()


def _restore(pane, selected, cursor):
	pane.clear_selection()
	if selected:
		pane.select(selected)
	if cursor is not None:
		pane.place_cursor_at(cursor)


def _can_swap(panes):
	return len(panes) > 1 and not _any_pane_hidden(panes)
