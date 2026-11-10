from fman.impl.view import ProxyStyle
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import (
	QApplication, QProxyStyle, QStyle, QStyleOptionHeader, QTableView,
	QStyleFactory,
)
from unittest import TestCase

from fman.impl.view.header_sort_arrow import SortArrowPosition


class RecordingStyle(QProxyStyle):
	def __init__(self, base_style):
		super().__init__(base_style)
		self.arrow_rects = []
		self.label_rects = []

	def drawPrimitive(self, element, option, painter, widget=None):
		if element == QStyle.PE_IndicatorHeaderArrow:
			self.arrow_rects.append(QRect(option.rect))
		super().drawPrimitive(element, option, painter, widget)

	def drawControl(self, element, option, painter, widget=None):
		if element == QStyle.CE_HeaderLabel and \
			isinstance(option, QStyleOptionHeader) and option.text == 'Name' and \
			option.sortIndicator != QStyleOptionHeader.None_:
			self.label_rects.append(QRect(option.rect))
		super().drawControl(element, option, painter, widget)


class HeaderSortArrowTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def _paint_header(self, position, stylesheet):
		view = QTableView()
		view.resize(480, 200)
		model = QStandardItemModel(1, 2)
		model.setHorizontalHeaderLabels(['Name', 'Size'])
		view.setModel(model)
		view.setColumnWidth(0, 300)
		view.setSortingEnabled(True)
		view.sortByColumn(0, Qt.AscendingOrder)
		if stylesheet:
			view.setStyleSheet('QHeaderView::section { padding: 1ex; }')
		recording_style = RecordingStyle(
			QStyleFactory.create(QApplication.style().objectName())
		)
		style = ProxyStyle(recording_style, position)
		style.setParent(view)
		view.setStyle(style)
		view.horizontalHeader().setStyle(style)
		view.show()
		self.app.processEvents()
		view.horizontalHeader().grab()
		self.app.processEvents()
		header = view.horizontalHeader()
		result = (
			recording_style.arrow_rects[-1],
			recording_style.label_rects[-1],
			header.sectionViewportPosition(0) + header.sectionSize(0) // 2
		)
		view.close()
		view.deleteLater()
		self.app.processEvents()
		return result

	def test_after_places_arrow_beside_label_with_and_without_stylesheet(self):
		for stylesheet in (False, True):
			with self.subTest(stylesheet=stylesheet):
				arrow, label, _ = self._paint_header(
					SortArrowPosition.AFTER, stylesheet
				)
				self.assertLess(arrow.left(), 150)
				self.assertGreater(arrow.left(), label.left())

	def test_before_places_arrow_before_shifted_label(self):
		for stylesheet in (False, True):
			with self.subTest(stylesheet=stylesheet):
				arrow, label, _ = self._paint_header(
					SortArrowPosition.BEFORE, stylesheet
				)
				self.assertLess(arrow.left(), label.left())

	def test_edge_keeps_arrow_at_the_right_side_of_the_section(self):
		for stylesheet in (False, True):
			with self.subTest(stylesheet=stylesheet):
				arrow, _, section_midpoint = self._paint_header(
					SortArrowPosition.EDGE, stylesheet
				)
				self.assertGreater(arrow.left() + arrow.width(), section_midpoint)
