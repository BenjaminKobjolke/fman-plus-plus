"""Run via tools\\run_view_tests.bat; this suite owns a QApplication."""

from fman.impl.view.scroll_margin import ScrollMargin
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QApplication, QAbstractItemView
from unittest import TestCase


class ScrollMarginTest(TestCase):
	def setUp(self):
		super().setUp()
		self._view = ScrollMargin()
		self._view.verticalHeader().setMinimumSectionSize(0)
		self._view.setModel(QStandardItemModel(100, 1))
		self._view.show()
		self.app.processEvents()
		row_height = self._view.get_row_height()
		header_height = self._view.horizontalHeader().height()
		frame_width = self._view.frameWidth()
		self._view.resize(400, row_height * 10 + header_height + 2 * frame_width)
		self.app.processEvents()
		self.addCleanup(self._view.deleteLater)

	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def _move_to(self, row, hint=QAbstractItemView.EnsureVisible):
		index = self._view.model().index(row, 0)
		if hint == QAbstractItemView.EnsureVisible:
			self._view.setCurrentIndex(index)
		else:
			self._view.scrollTo(index, hint)
		self.app.processEvents()

	def _first_visible_row(self):
		return self._view.verticalScrollBar().value()

	def test_zero_margin_preserves_qt_scrolling(self):
		self._view.set_scroll_margin(0)
		self._move_to(9)
		self.assertEqual(self._first_visible_row(), 0)
		self._move_to(10)
		self.assertEqual(self._first_visible_row(), 1)

	def test_margin_keeps_rows_visible_above_and_below_cursor(self):
		self._view.set_scroll_margin(3)
		self._move_to(6)
		self.assertEqual(self._first_visible_row(), 0)
		self._move_to(7)
		self.assertEqual(self._first_visible_row(), 1)
		self._move_to(50)
		self.assertEqual(self._first_visible_row(), 44)
		self._move_to(46)
		self.assertEqual(self._first_visible_row(), 43)

	def test_margin_shrinks_at_list_ends(self):
		self._view.set_scroll_margin(3)
		self._move_to(99)
		self.assertEqual(self._first_visible_row(), 90)
		self._move_to(0)
		self.assertEqual(self._first_visible_row(), 0)

	def test_huge_margin_centers_current_row(self):
		self._view.set_scroll_margin(100)
		self._move_to(50)
		self.assertEqual(self._first_visible_row(), 46)

	def test_explicit_position_hint_is_unchanged(self):
		self._view.set_scroll_margin(3)
		self._move_to(50, QAbstractItemView.PositionAtTop)
		self.assertEqual(self._first_visible_row(), 50)
