from core.commands import pane_view
from core.commands.pane_view import ShowAllPanes, ShowOnlyActivePane, \
	AddPane, RemovePane, SwitchPanes
from core.folder_tree_view import FolderTreeView
from PyQt5.QtGui import QFont
from core.tests.commands import FakeWindow
from PyQt5.QtWidgets import QApplication
from unittest.mock import patch, Mock
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

class RememberBasePaneFontSizeTest(TestCase):
	def test_uses_polished_view_font(self):
		class FileView:
			def __init__(self):
				self.polished = False
			def ensurePolished(self):
				self.polished = True
			def font(self):
				return QFont(_APP.font().family(), 20 if self.polished else 9)

		class Widget:
			def __init__(self):
				self._file_view = FileView()

		class Pane:
			def __init__(self):
				self._widget = Widget()

		previous_base_size = pane_view._base_pane_font_size
		try:
			pane_view._base_pane_font_size = None
			with patch.object(
				pane_view, 'effective_font_size',
				side_effect=lambda get_font: get_font().pointSize()
			):
				pane_view._remember_base_pane_font_size(Pane())
			self.assertEqual(20, pane_view._base_pane_font_size)
		finally:
			pane_view._base_pane_font_size = previous_base_size

class ApplyPaneFontSizeTest(TestCase):
	def test_applies_font_size_to_a_mounted_folder_tree(self):
		pane = Mock()
		tree = Mock(spec=FolderTreeView)
		pane.get_mounted_widget.return_value = tree

		pane_view._apply_pane_font_size(pane, 16)

		tree.set_font_size.assert_called_once_with(16)
	def test_ignores_other_or_missing_mounted_widgets(self):
		for mounted in (None, object()):
			with self.subTest(mounted=mounted):
				pane = Mock()
				pane.get_mounted_widget.return_value = mounted

				pane_view._apply_pane_font_size(pane, None)

				pane._widget.set_file_list_style_sheet.assert_called_once_with('')
				pane.get_mounted_widget.assert_called_once_with()

	def test_styles_both_file_view_modes_through_the_pane_widget(self):
		pane = Mock()

		pane_view._apply_pane_font_size(pane, 16)

		pane._widget.set_file_list_style_sheet.assert_called_once_with(
			'FileListView, CompactFileView { font-size: 16pt; }'
		)
	def test_clears_the_override_through_the_pane_widget(self):
		pane = Mock()

		pane_view._apply_pane_font_size(pane, None)

		pane._widget.set_file_list_style_sheet.assert_called_once_with('')

class ApplyZoomScaleTest(TestCase):
	def setUp(self):
		self.previous_base_size = pane_view._base_pane_font_size
		self.addCleanup(self._restore_base_size)
	def _restore_base_size(self):
		pane_view._base_pane_font_size = self.previous_base_size
	def test_uses_point_offset_and_keeps_icon_scaling_proportional(self):
		pane_view._base_pane_font_size = 9
		with patch.object(pane_view, 'set_icon_scale') as set_icon_scale, \
				patch.object(pane_view, 'set_palette_font_offset') as set_font_offset:
			pane_view._apply_zoom_scale(12)
		set_icon_scale.assert_called_once_with(12 / 9)
		set_font_offset.assert_called_once_with(3)
	def test_zero_offset_keeps_proportional_icon_scaling(self):
		pane_view._base_pane_font_size = 12
		with patch.object(pane_view, 'set_icon_scale') as set_icon_scale, \
				patch.object(pane_view, 'set_palette_font_offset') as set_font_offset:
			pane_view._apply_zoom_scale(12)
		set_icon_scale.assert_called_once_with(1.0)
		set_font_offset.assert_called_once_with(0)
	def test_unavailable_zoom_resets_both_scales(self):
		pane_view._base_pane_font_size = None
		with patch.object(pane_view, 'set_icon_scale') as set_icon_scale, \
				patch.object(pane_view, 'set_palette_font_offset') as set_font_offset:
			pane_view._apply_zoom_scale(18)
		set_icon_scale.assert_called_once_with(1.0)
		set_font_offset.assert_called_once_with(0)

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
