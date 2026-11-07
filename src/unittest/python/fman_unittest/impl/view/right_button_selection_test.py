"""Right-button selection tests use a QApplication of their own."""

from fman.impl.view import FileListView
from fman.impl.view.compact_view import CompactFileView
from PyQt5.QtCore import QEvent, QPointF, Qt, pyqtSignal
from PyQt5.QtGui import QContextMenuEvent, QMouseEvent, QStandardItemModel
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import ANY, Mock


class SelectionModel(QStandardItemModel):
	sort_order_changed = pyqtSignal(int, int)
	transaction_ended = pyqtSignal()

	def __init__(self):
		super().__init__(5, 1)

	def find(self, url):
		row = int(url[len('file://'):])
		return self.index(row, 0)

	def url(self, index):
		return 'file://%d' % index.row()

	def row_is_loaded(self, row):
		return True

	def get_location(self):
		return 'file://'

	def load_rows(self, rows, callback=None):
		if callback:
			callback()


class RightButtonSelectionTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.model = SelectionModel()
		self.get_context_menu = Mock(return_value=[])
		self.view = FileListView(None, self.get_context_menu)
		self.view.setModel(self.model)
		self.view.resize(320, 240)
		self.addCleanup(self.view.deleteLater)

	def test_mode_off_keeps_right_click_and_move_out_of_selection(self):
		self.view.set_right_button_selection(False)
		self._mouse(QEvent.MouseButtonPress, 0, Qt.RightButton, Qt.RightButton)
		self._mouse(QEvent.MouseButtonRelease, 0, Qt.RightButton, Qt.NoButton)
		self._mouse_at(
			QEvent.MouseMove, self.view.viewport().rect().bottomRight(),
			Qt.NoButton, Qt.RightButton)
		self.assertEqual([], self._selected_rows())

	def test_right_press_toggles_row_and_moves_cursor(self):
		self.view.set_right_button_selection(True)
		self._mouse(QEvent.MouseButtonPress, 2, Qt.RightButton, Qt.RightButton)
		self.assertEqual([2], self._selected_rows())
		self.assertEqual(2, self.view.currentIndex().row())
		self._mouse(QEvent.MouseButtonRelease, 2, Qt.RightButton, Qt.NoButton)
		self._mouse(QEvent.MouseButtonPress, 2, Qt.RightButton, Qt.RightButton)
		self.assertEqual([], self._selected_rows())

	def test_drag_paints_press_state_across_rows(self):
		self.view.set_right_button_selection(True)
		self._mouse(QEvent.MouseButtonPress, 0, Qt.RightButton, Qt.RightButton)
		self._mouse(QEvent.MouseMove, 3, Qt.NoButton, Qt.RightButton)
		self.assertEqual([0, 1, 2, 3], self._selected_rows())

	def test_drag_from_selected_row_deselects_rows_passed_over(self):
		self.view.select(['file://0', 'file://1', 'file://2', 'file://3'])
		self.view.set_right_button_selection(True)
		self._mouse(QEvent.MouseButtonPress, 0, Qt.RightButton, Qt.RightButton)
		self._mouse(QEvent.MouseMove, 3, Qt.NoButton, Qt.RightButton)
		self.assertEqual([], self._selected_rows())

	def test_hold_menu_keeps_earlier_selection_and_selects_held_row(self):
		self.view.set_right_button_selection(True)
		self.view.select(['file://4'])
		self._mouse(QEvent.MouseButtonPress, 1, Qt.RightButton, Qt.RightButton)
		self.view._hold_timer.timeout.emit()
		self.assertEqual([1, 4], self._selected_rows())
		self.get_context_menu.assert_called_once()
		self.assertEqual('file://1', self.get_context_menu.call_args.args[1])

	def test_hold_menu_reselects_row_that_press_toggled_off(self):
		self.view.set_right_button_selection(True)
		self.view.select(['file://1', 'file://4'])
		self._mouse(QEvent.MouseButtonPress, 1, Qt.RightButton, Qt.RightButton)
		self.assertEqual([4], self._selected_rows())
		self.view._hold_timer.timeout.emit()
		self.assertEqual([1, 4], self._selected_rows())

	def test_leaving_start_row_or_entering_empty_space_stops_hold_timer(self):
		self.view.set_right_button_selection(True)
		self._mouse(QEvent.MouseButtonPress, 0, Qt.RightButton, Qt.RightButton)
		self._mouse(QEvent.MouseMove, 1, Qt.NoButton, Qt.RightButton)
		self.assertFalse(self.view._hold_timer.isActive())
		self._mouse(QEvent.MouseButtonRelease, 1, Qt.RightButton, Qt.NoButton)
		self._mouse(QEvent.MouseButtonPress, 0, Qt.RightButton, Qt.RightButton)
		pos = self.view.viewport().rect().bottomRight()
		self._mouse_at(QEvent.MouseMove, pos, Qt.NoButton, Qt.RightButton)
		self.assertFalse(self.view._hold_timer.isActive())

	def test_releasing_right_button_stops_hold_timer(self):
		self.view.set_right_button_selection(True)
		self._mouse(QEvent.MouseButtonPress, 0, Qt.RightButton, Qt.RightButton)
		self._mouse(QEvent.MouseButtonRelease, 0, Qt.RightButton, Qt.NoButton)
		self.assertFalse(self.view._hold_timer.isActive())
		self.assertIsNone(self.view._right_button_selection_start)

	def test_mouse_context_event_on_row_is_swallowed_but_other_reasons_are_not(self):
		self.view.set_right_button_selection(True)
		pos = self._pos(0)
		mouse = QContextMenuEvent(QContextMenuEvent.Mouse, pos)
		QApplication.sendEvent(self.view.viewport(), mouse)
		self.get_context_menu.assert_not_called()
		keyboard = QContextMenuEvent(QContextMenuEvent.Keyboard, pos)
		QApplication.sendEvent(self.view.viewport(), keyboard)
		self.get_context_menu.assert_called_once()

	def test_mouse_context_event_on_empty_space_opens_menu(self):
		self.view.set_right_button_selection(True)
		pos = self.view.viewport().rect().bottomRight()
		QApplication.sendEvent(
			self.view.viewport(), QContextMenuEvent(QContextMenuEvent.Mouse, pos)
		)
		self.get_context_menu.assert_called_once_with(ANY, None)

	def test_compact_view_uses_file_view_setting_for_right_click(self):
		self.view.set_right_button_selection(True)
		compact = CompactFileView(self.view)
		compact.setModel(self.model)
		compact.setSelectionModel(self.view.selectionModel())
		compact.resize(320, 240)
		compact.show()
		self.app.processEvents()
		self.addCleanup(compact.deleteLater)
		pos = compact.visualRect(self.model.index(2, 0)).center()
		QApplication.sendEvent(compact.viewport(), QMouseEvent(
			QEvent.MouseButtonPress, QPointF(pos), Qt.RightButton,
			Qt.RightButton, Qt.NoModifier
		))
		self.assertEqual([2], self._selected_rows())

	def _mouse(self, event_type, row, button, buttons):
		self._mouse_at(event_type, self._pos(row), button, buttons)

	def _mouse_at(self, event_type, pos, button, buttons):
		QApplication.sendEvent(self.view.viewport(), QMouseEvent(
			event_type, QPointF(pos), button, buttons, Qt.NoModifier
		))

	def _pos(self, row):
		return self.view.visualRect(self.model.index(row, 0)).center()

	def _selected_rows(self):
		return sorted(
			index.row() for index in self.view.selectionModel().selectedRows()
		)
