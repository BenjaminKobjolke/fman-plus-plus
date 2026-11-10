"""Pane status messages stay with their pane and clear safely."""

from fman.impl.pane_status import PaneStatusLine, PaneStatusMode
from fman import DirectoryPane
from fman.impl.widgets import MainWindow
from PyQt5.QtWidgets import QApplication, QSizePolicy, QWidget
from unittest import TestCase
from unittest.mock import MagicMock, patch


_APP = QApplication.instance() or QApplication([])


class PaneStatusLineTest(TestCase):

	def setUp(self):
		self.line = PaneStatusLine()

	def tearDown(self):
		self.line.deleteLater()

	def test_is_hidden_until_a_message_is_set(self):
		self.assertFalse(self.line.isVisible())
		self.line.set_status_message('Saved')
		self.assertEqual('Saved', self.line.text())
		self.assertTrue(self.line.isVisible())

	def test_clear_hides_and_empties_the_line(self):
		self.line.set_status_message('Saved')
		self.line.clear_status_message()
		self.assertEqual('', self.line.text())
		self.assertFalse(self.line.isVisible())

	def test_disabled_line_keeps_message_but_stays_hidden(self):
		self.line.set_status_line_visible(False)
		self.line.set_status_message('Saved')
		self.assertEqual('Saved', self.line.text())
		self.assertFalse(self.line.isVisible())
		self.line.set_status_line_visible(True)
		self.assertTrue(self.line.isVisible())

	def test_timer_clears_timed_message(self):
		self.line.set_status_message('Saved', timeout_secs=1)
		self.assertTrue(self.line._timer.isSingleShot())
		self.assertEqual(1000, self.line._timer.interval())
		self.line._timer.timeout.emit()
		self.assertEqual('', self.line.text())
		self.assertFalse(self.line.isVisible())

	def test_idle_text_is_shown_until_a_message_arrives(self):
		self.line.set_idle_text('3 files selected')
		self.assertEqual('3 files selected', self.line.text())
		self.assertTrue(self.line.isVisible())
		self.line.set_status_message('Saved')
		self.assertEqual('Saved', self.line.text())

	def test_clearing_message_restores_idle_text(self):
		self.line.set_idle_text('3 files selected')
		self.line.set_status_message('Saved')
		self.line.clear_status_message()
		self.assertEqual('3 files selected', self.line.text())
		self.assertTrue(self.line.isVisible())

	def test_timed_message_restores_idle_text(self):
		self.line.set_idle_text('3 files selected')
		self.line.set_status_message('Saved', timeout_secs=1)
		self.line._timer.timeout.emit()
		self.assertEqual('3 files selected', self.line.text())
		self.assertTrue(self.line.isVisible())

	def test_empty_idle_text_keeps_line_hidden(self):
		self.line.set_idle_text('3 files selected')
		self.line.set_idle_text('')
		self.assertEqual('', self.line.text())
		self.assertFalse(self.line.isVisible())

	def test_disabled_line_keeps_idle_text_but_stays_hidden(self):
		self.line.set_status_line_visible(False)
		self.line.set_idle_text('3 files selected')
		self.assertEqual('3 files selected', self.line.text())
		self.assertFalse(self.line.isVisible())
		self.line.set_status_line_visible(True)
		self.assertTrue(self.line.isVisible())

	def test_external_links_are_opened_by_the_label(self):
		self.assertTrue(self.line.openExternalLinks())

	def test_line_uses_font_height_and_can_shrink_horizontally(self):
		policy = self.line.sizePolicy()
		self.assertEqual(QSizePolicy.Fixed, policy.verticalPolicy())
		self.assertEqual(QSizePolicy.Ignored, policy.horizontalPolicy())


class MainWindowPaneStatusTest(TestCase):

	def setUp(self):
		self.window = MainWindow(None, [], None, None, None, None)
		self.addCleanup(self.window.deleteLater)
		self.left = MagicMock()
		self.right = MagicMock()
		self.window._panes = [self.left, self.right]

	def test_default_mode_routes_to_pane_and_window(self):
		self.window.show_pane_status_message(self.left, 'Left message')
		self.left.set_status_message.assert_called_once_with(
			'Left message', None)
		self.assertEqual('Left message', self.window._status_bar_text.text())

	def test_pane_only_mode_does_not_replace_window_message(self):
		self.window.show_status_message('Window message')
		self.window.set_pane_status_mode(PaneStatusMode(True, False))
		self.window.show_pane_status_message(self.left, 'Left message')
		self.left.set_status_message.assert_called_once_with(
			'Left message', None)
		self.assertEqual('Window message', self.window._status_bar_text.text())

	def test_hidden_lines_route_to_window_bar(self):
		self.window.set_pane_status_mode(PaneStatusMode(False, False))
		self.window.show_pane_status_message(self.left, 'Left message')
		self.left.set_status_message.assert_called_once_with(
			'Left message', None)
		self.assertEqual('Left message', self.window._status_bar_text.text())

	def test_clear_only_clears_window_bar_owned_by_that_pane(self):
		self.window.show_pane_status_message(self.left, 'Left message')
		self.window.clear_pane_status_message(self.right)
		self.assertEqual('Left message', self.window._status_bar_text.text())
		self.window.clear_pane_status_message(self.left)
		self.assertEqual('Ready.', self.window._status_bar_text.text())

	def test_clearing_pane_message_does_not_clear_later_window_message(self):
		self.window.show_pane_status_message(self.left, 'Left message')
		self.window.show_status_message('Window message')
		self.window.clear_pane_status_message(self.left)
		self.assertEqual('Window message', self.window._status_bar_text.text())

	def test_mode_is_applied_to_existing_and_new_panes(self):
		self.window.set_pane_status_mode(PaneStatusMode(False, True))
		self.left.set_status_line_visible.assert_called_once_with(False)
		self.right.set_status_line_visible.assert_called_once_with(False)
		self.assertEqual(PaneStatusMode(False, True), self.window._pane_status_mode)

	def test_mode_is_applied_when_a_pane_is_added(self):
		self.window._pane_status_mode = PaneStatusMode(False, True)
		pane = QWidget()
		pane.set_icon_size = MagicMock()
		pane.set_scroll_margin = MagicMock()
		pane.set_right_button_selection = MagicMock()
		pane.set_drag_selection = MagicMock()
		pane.set_status_line_visible = MagicMock()
		pane.set_backgrounds = MagicMock()
		with patch('fman.impl.widgets.DirectoryPaneWidget', return_value=pane):
			self.window.add_pane()
		pane.set_status_line_visible.assert_called_once_with(False)

	def test_right_button_selection_mode_is_applied_to_existing_panes(self):
		self.window.set_right_button_selection(True)
		self.assertTrue(self.window._right_button_selection)
		self.left.set_right_button_selection.assert_called_once_with(True)
		self.right.set_right_button_selection.assert_called_once_with(True)

	def test_right_button_selection_mode_is_applied_when_a_pane_is_added(self):
		self.window.set_right_button_selection(True)
		pane = QWidget()
		pane.set_icon_size = MagicMock()
		pane.set_scroll_margin = MagicMock()
		pane.set_right_button_selection = MagicMock()
		pane.set_drag_selection = MagicMock()
		pane.set_status_line_visible = MagicMock()
		pane.set_backgrounds = MagicMock()
		with patch('fman.impl.widgets.DirectoryPaneWidget', return_value=pane):
			self.window.add_pane()
		pane.set_right_button_selection.assert_called_once_with(True)

	def test_drag_selection_mode_is_applied_to_existing_panes(self):
		self.window.set_drag_selection(False)
		self.assertFalse(self.window._drag_selection)
		self.left.set_drag_selection.assert_called_once_with(False)
		self.right.set_drag_selection.assert_called_once_with(False)

	def test_drag_selection_mode_is_applied_when_a_pane_is_added(self):
		self.window.set_drag_selection(False)
		pane = QWidget()
		pane.set_icon_size = MagicMock()
		pane.set_scroll_margin = MagicMock()
		pane.set_right_button_selection = MagicMock()
		pane.set_drag_selection = MagicMock()
		pane.set_status_line_visible = MagicMock()
		pane.set_backgrounds = MagicMock()
		with patch('fman.impl.widgets.DirectoryPaneWidget', return_value=pane):
			self.window.add_pane()
		pane.set_drag_selection.assert_called_once_with(False)

	def test_idle_text_is_routed_by_placement_flags(self):
		self.window.set_pane_idle_status(
			self.left, '3 files selected', pane_line=True, status_bar=True)
		self.left.set_idle_status_message.assert_called_once_with(
			'3 files selected')
		self.assertEqual('3 files selected', self.window._status_bar_text.text())

	def test_transient_window_message_takes_priority_then_idle_returns(self):
		self.left.hasFocus.return_value = True
		self.window.set_pane_idle_status(
			self.left, '3 files selected', pane_line=False, status_bar=True)
		self.window.show_status_message('Saved', timeout_secs=1)
		self.assertEqual('Saved', self.window._status_bar_text.text())
		self.window._timer.timeout.emit()
		self.assertEqual('3 files selected', self.window._status_bar_text.text())

	def test_idle_status_bar_tracks_focused_pane(self):
		self.left.hasFocus.return_value = True
		self.right.hasFocus.return_value = False
		self.window.set_pane_idle_status(
			self.left, 'Left summary', pane_line=False, status_bar=True)
		self.window.set_pane_idle_status(
			self.right, 'Right summary', pane_line=False, status_bar=True)
		self.assertEqual('Left summary', self.window._status_bar_text.text())
		self.right.hasFocus.return_value = True
		self.left.hasFocus.return_value = False
		self.window.set_pane_idle_status(
			self.right, 'Right summary', pane_line=False, status_bar=True)
		self.assertEqual('Right summary', self.window._status_bar_text.text())


class DirectoryPaneStatusApiTest(TestCase):

	def setUp(self):
		self.window = MagicMock()
		self.widget = MagicMock()
		self.pane = DirectoryPane(self.window, self.widget, MagicMock())

	def test_show_delegates_message_and_timeout(self):
		self.pane.show_status_message('Saved', timeout_secs=3)
		self.window._widget.show_pane_status_message.assert_called_once_with(
			self.widget, 'Saved', 3)

	def test_clear_delegates_pane_identity(self):
		self.pane.clear_status_message()
		self.window._widget.clear_pane_status_message.assert_called_once_with(
			self.widget)

	def test_set_idle_status_delegates_text_and_placement(self):
		self.pane.set_idle_status_message(
			'Summary', pane_line=True, status_bar=False)
		self.window._widget.set_pane_idle_status.assert_called_once_with(
			self.widget, 'Summary', True, False)
