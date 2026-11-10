"""Drag-range selection tests use a QApplication of their own."""

from fman.impl.view import FileListView
from fman.impl.view.compact_view import CompactFileView
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt, pyqtSignal
from PyQt5.QtGui import QCursor, QMouseEvent, QStandardItemModel
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock


class SelectionModel(QStandardItemModel):
	sort_order_changed = pyqtSignal(int, int)
	transaction_ended = pyqtSignal()

	def __init__(self):
		super().__init__(40, 2)
		for row in range(self.rowCount()):
			self.setData(self.index(row, 0), 'file %d' % row)
		self.setData(self.index(self.rowCount() - 1, 0),
			'a deliberately long filename for compact whitespace')

	def find(self, url):
		return self.index(int(url[len('file://'):]), 0)

	def url(self, index):
		return 'file://%d' % index.row()

	def row_is_loaded(self, row):
		return True

	def set_num_rows_to_preload(self, _):
		pass

	def get_columns(self):
		return [
			Mock(
				get_qualified_name=Mock(return_value='Name'),
				get_widest_str=Mock(return_value='')
			),
			Mock(
				get_qualified_name=Mock(return_value='Other'),
				get_widest_str=Mock(return_value='')
			)
		]

	def get_location(self):
		return 'file://'

	def load_rows(self, rows, callback=None):
		if callback:
			callback()


class DragRangeSelectionTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.model = SelectionModel()
		self.view = FileListView(None, Mock(return_value=[]))
		self.view.setModel(self.model)
		self.view.resize(320, 120)
		self.view.show()
		self.app.processEvents()
		self.addCleanup(self.view.deleteLater)

	def test_plain_drag_clears_existing_selection(self):
		self.view.select(['file://0'])
		self._drag(1, 3)
		self.assertEqual([1, 2, 3], self._selected_rows())

	def test_control_drag_keeps_existing_selection(self):
		self.view.select(['file://0'])
		self._drag(1, 3, Qt.ControlModifier)
		self.assertEqual([0, 1, 2, 3], self._selected_rows())

	def test_dragging_back_shrinks_the_range(self):
		self._press(1)
		self._move(4)
		self._move(2)
		self._release(2)
		self.assertEqual([1, 2], self._selected_rows())

	def test_drag_from_name_starts_file_drag(self):
		self._mouse(QEvent.MouseButtonPress, self._name_pos(1), Qt.LeftButton,
			Qt.LeftButton)
		self._mouse(QEvent.MouseMove, self._name_pos(3), Qt.NoButton,
			Qt.LeftButton)
		self.assertEqual(self.view.DraggingState, self.view.state())
		self.assertEqual([], self._selected_rows())

	def test_disabled_mode_keeps_file_drag_behavior(self):
		self.view.set_drag_selection(False)
		self._mouse(QEvent.MouseButtonPress, self._whitespace_pos(1),
			Qt.LeftButton, Qt.LeftButton)
		self._mouse(QEvent.MouseMove, self._whitespace_pos(3), Qt.NoButton,
			Qt.LeftButton)
		self.assertEqual(self.view.DraggingState, self.view.state())
		self.assertEqual([], self._selected_rows())

	def test_short_movement_does_not_change_selection(self):
		self.view.select(['file://0'])
		start = self._whitespace_pos(1)
		self._mouse(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton)
		end = start + QPoint(max(1, QApplication.startDragDistance() - 1), 0)
		self._mouse(QEvent.MouseMove, end, Qt.NoButton, Qt.LeftButton)
		self._mouse(QEvent.MouseButtonRelease, end, Qt.LeftButton, Qt.NoButton)
		self.assertEqual([0], self._selected_rows())

	def test_press_below_last_row_can_drag_up(self):
		self.view.resize(320, 1200)
		self.app.processEvents()
		last = self.model.rowCount() - 1
		pos = QPoint(
			self.view.viewport().rect().left(),
			self.view.viewport().rect().bottom() + 1
		)
		self._mouse(QEvent.MouseButtonPress, pos, Qt.LeftButton, Qt.LeftButton)
		self._mouse(QEvent.MouseMove, self._whitespace_pos(last - 2),
			Qt.NoButton, Qt.LeftButton)
		self._mouse(QEvent.MouseButtonRelease, self._whitespace_pos(last - 2),
			Qt.LeftButton, Qt.NoButton)
		self.assertEqual([last - 2, last - 1, last], self._selected_rows())

	def test_drag_below_viewport_scrolls_and_extends_range(self):
		self._press(1)
		outside = QPoint(self._whitespace_pos(1).x(),
			self.view.viewport().height() + 1)
		self._mouse(QEvent.MouseMove, outside, Qt.NoButton, Qt.LeftButton)
		self.assertTrue(self.view._drag_selection_scroll_timer.isActive())
		QCursor.setPos(self.view.viewport().mapToGlobal(outside))
		before = self.view.verticalScrollBar().value()
		self.view._drag_selection_scroll_timer.timeout.emit()
		self.assertGreater(self.view.verticalScrollBar().value(), before)
		self.assertGreater(max(self._selected_rows()), 1)
		self._release(1)
		self.assertFalse(self.view._drag_selection_scroll_timer.isActive())

	def test_compact_view_uses_file_view_setting(self):
		compact = CompactFileView(self.view)
		compact.setModel(self.model)
		compact.setSelectionModel(self.view.selectionModel())
		compact.resize(320, 120)
		compact.show()
		self.app.processEvents()
		self.addCleanup(compact.deleteLater)
		start = compact.visualRect(self.model.index(1, 0)).center()
		end = compact.visualRect(self.model.index(3, 0)).center()
		start.setX(compact.visualRect(self.model.index(1, 0)).right() - 1)
		end.setX(compact.visualRect(self.model.index(3, 0)).right() - 1)
		self._send(compact, QEvent.MouseButtonPress, start, Qt.LeftButton,
			Qt.LeftButton)
		self._send(compact, QEvent.MouseMove, end, Qt.NoButton, Qt.LeftButton)
		self._send(compact, QEvent.MouseButtonRelease, end, Qt.LeftButton,
			Qt.NoButton)
		self.assertEqual([1, 2, 3], self._selected_rows())

	def _drag(self, start_row, end_row, modifiers=Qt.NoModifier):
		self._mouse(QEvent.MouseButtonPress, self._whitespace_pos(start_row),
			Qt.LeftButton, Qt.LeftButton, modifiers)
		self._mouse(QEvent.MouseMove, self._whitespace_pos(end_row),
			Qt.NoButton, Qt.LeftButton, modifiers)
		self._mouse(QEvent.MouseButtonRelease, self._whitespace_pos(end_row),
			Qt.LeftButton, Qt.NoButton, modifiers)

	def _press(self, row):
		self._mouse(QEvent.MouseButtonPress, self._whitespace_pos(row),
			Qt.LeftButton, Qt.LeftButton)

	def _move(self, row):
		self._mouse(QEvent.MouseMove, self._whitespace_pos(row),
			Qt.NoButton, Qt.LeftButton)

	def _release(self, row):
		self._mouse(QEvent.MouseButtonRelease, self._whitespace_pos(row),
			Qt.LeftButton, Qt.NoButton)

	def _mouse(self, event_type, pos, button, buttons, modifiers=Qt.NoModifier):
		self._send(self.view, event_type, pos, button, buttons, modifiers)

	def _send(self, view, event_type, pos, button, buttons,
			modifiers=Qt.NoModifier):
		QApplication.sendEvent(view.viewport(), QMouseEvent(
			event_type, QPointF(pos), button, buttons, modifiers
		))

	def _name_pos(self, row):
		rect = self.view.visualRect(self.model.index(row, 0))
		return QPoint(rect.left() + 1, rect.center().y())

	def _whitespace_pos(self, row):
		return self.view.visualRect(self.model.index(row, 1)).center()

	def _selected_rows(self):
		return sorted(index.row() for index in
			self.view.selectionModel().selectedRows())
