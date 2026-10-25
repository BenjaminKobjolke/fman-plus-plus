from core.commands.pane_view import ShowAllPanes, ShowOnlyActivePane, \
	AddPane, RemovePane, SwitchPanes
from core.tests.commands import FakeWindow
from PyQt5.QtWidgets import QApplication
from unittest import TestCase

# ShowOnlyActivePane is decorated with @run_in_main_thread, which needs a
# QApplication instance to exist (even though it never enters its event
# loop here, since the test runs on the same thread it dispatches to).
# Keep a module-level reference so it isn't garbage-collected:
_APP = QApplication.instance() or QApplication([])

class _FakeWidget:
	def __init__(self, visible=True):
		self._visible = visible
	def isVisible(self):
		return self._visible
	def setVisible(self, visible):
		self._visible = visible

class _FakePane:
	def __init__(self, window, path='file:///current'):
		self.window = window
		self._widget = _FakeWidget()
		self.focused = False
		self.path = path
		self.set_path_calls = []
	def focus(self):
		self.focused = True
	def get_path(self):
		return self.path
	def set_path(self, path, callback=None):
		self.set_path_calls.append(path)
		if callback:
			callback()

def _two_pane_window():
	window = FakeWindow()
	active, other = _FakePane(window), _FakePane(window)
	window._panes = [active, other]
	return window, active, other

class ShowOnlyActivePaneTest(TestCase):
	def test_hides_other_panes(self):
		window, active, other = _two_pane_window()
		ShowOnlyActivePane(active)()
		self.assertTrue(active._widget.isVisible())
		self.assertFalse(other._widget.isVisible())
		self.assertTrue(active.focused)
	def test_visible_only_with_multiple_panes_all_shown(self):
		window, active, other = _two_pane_window()
		self.assertTrue(ShowOnlyActivePane(active).is_visible())
		other._widget.setVisible(False)
		self.assertFalse(ShowOnlyActivePane(active).is_visible())
		window._panes = [active]
		self.assertFalse(ShowOnlyActivePane(active).is_visible())

class SwitchPanesTest(TestCase):
	def test_switches_to_visible_pane(self):
		window, active, other = _two_pane_window()
		SwitchPanes(active)()
		self.assertTrue(other.focused)
	def test_does_not_switch_to_hidden_pane(self):
		window, active, other = _two_pane_window()
		ShowOnlyActivePane(active)()
		SwitchPanes(active)()
		self.assertFalse(other.focused)
	def test_ignores_out_of_range_pane_index(self):
		window, active, other = _two_pane_window()
		SwitchPanes(active)(pane_index=2)
		self.assertFalse(active.focused)
		self.assertFalse(other.focused)

class AddPaneTest(TestCase):
	def test_adds_pane_at_current_path_and_focuses_it(self):
		window, active, _ = _two_pane_window()
		def add_pane():
			pane = _FakePane(window)
			window._panes.append(pane)
			return pane
		window.add_pane = add_pane
		command = AddPane(active)
		command()
		self.assertEqual(3, len(window._panes))
		new_pane = window._panes[-1]
		self.assertEqual([active.get_path()], new_pane.set_path_calls)
		self.assertTrue(new_pane.focused)
	def test_hidden_pane_hides_command(self):
		window, active, other = _two_pane_window()
		other._widget.setVisible(False)
		self.assertFalse(AddPane(active).is_visible())

class RemovePaneTest(TestCase):
	def test_removes_active_and_focuses_next_pane(self):
		window, active, other = _two_pane_window()
		third = _FakePane(window)
		window._panes.append(third)
		window.remove_pane = lambda pane: window._panes.remove(pane)
		RemovePane(other)()
		self.assertEqual([active, third], window._panes)
		self.assertTrue(third.focused)
	def test_removing_last_pane_focuses_first(self):
		window = FakeWindow()
		active, other = _FakePane(window), _FakePane(window)
		window._panes = [active, other]
		window.remove_pane = lambda pane: window._panes.remove(pane)
		RemovePane(other)()
		self.assertTrue(active.focused)
	def test_one_pane_is_hidden_and_call_is_noop(self):
		window = FakeWindow()
		pane = _FakePane(window)
		window._panes = [pane]
		window.remove_pane = lambda pane: self.fail('must not remove')
		command = RemovePane(pane)
		self.assertFalse(command.is_visible())
		command()
		self.assertFalse(pane.focused)
	def test_hidden_pane_hides_command(self):
		window, active, other = _two_pane_window()
		other._widget.setVisible(False)
		self.assertFalse(RemovePane(active).is_visible())

class ShowAllPanesTest(TestCase):
	def test_restores_all_panes(self):
		window, active, other = _two_pane_window()
		other._widget.setVisible(False)
		ShowAllPanes(active)()
		self.assertTrue(active._widget.isVisible())
		self.assertTrue(other._widget.isVisible())
		self.assertTrue(active.focused)
	def test_visible_only_when_a_pane_is_hidden(self):
		window, active, other = _two_pane_window()
		self.assertFalse(ShowAllPanes(active).is_visible())
		other._widget.setVisible(False)
		self.assertTrue(ShowAllPanes(active).is_visible())
