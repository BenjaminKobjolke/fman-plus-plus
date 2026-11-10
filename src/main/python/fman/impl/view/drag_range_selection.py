"""Contiguous left-button drag selection for file views."""

from PyQt5.QtCore import QItemSelection, QItemSelectionModel as QISM, \
	QPoint, Qt, QTimer
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication


AUTO_SCROLL_INTERVAL_MS = 50


class DragRangeSelection:
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._drag_selection = True
		self._press_pos = None
		self._start_row = None
		self._keep = False
		self._snapshot = None
		self._active = False
		self._last_drag_pos = None
		self._drag_selection_scroll_timer = QTimer(self)
		self._drag_selection_scroll_timer.setInterval(AUTO_SCROLL_INTERVAL_MS)
		self._drag_selection_scroll_timer.timeout.connect(self._auto_scroll)

	def set_drag_selection(self, enabled):
		self._drag_selection = enabled

	def _drag_selection_on(self):
		return self._drag_selection

	def _is_on_file_name(self, pos):
		index = self.indexAt(pos)
		if not index.isValid() or index.column() != 0:
			return False
		delegate = self.itemDelegate(index)
		name_width = delegate.sizeHint(self.viewOptions(), index).width()
		return pos.x() <= self.visualRect(index).left() + name_width

	def mousePressEvent(self, event):
		if self._drag_selection_on() and event.button() == Qt.LeftButton and \
				not self._is_on_file_name(event.pos()):
			model = self.model()
			if model is not None and model.rowCount():
				index = self.indexAt(event.pos())
				self._press_pos = QPoint(event.pos())
				self._start_row = index.row() if index.isValid() else \
					model.rowCount() - 1
				self._keep = bool(event.modifiers() & Qt.ControlModifier)
				self._snapshot = self.selectionModel().selection()
				self._active = False
				self._last_drag_pos = QPoint(event.pos())
		super().mousePressEvent(event)

	def mouseMoveEvent(self, event):
		if self._press_pos is not None and event.buttons() & Qt.LeftButton:
			self._last_drag_pos = QPoint(event.pos())
			if not self._active and \
					(event.pos() - self._press_pos).manhattanLength() >= \
					QApplication.startDragDistance():
				self._active = True
			if self._active:
				self._apply_range(event.pos())
				if self._outside_scroll_axis(event.pos()):
					self._drag_selection_scroll_timer.start()
				else:
					self._drag_selection_scroll_timer.stop()
				return
		super().mouseMoveEvent(event)

	def _apply_range(self, pos):
		model = self.model()
		if model is None or model.rowCount() == 0:
			return
		viewport_rect = self.viewport().rect()
		if viewport_rect.isEmpty():
			return
		pos = QPoint(
			max(viewport_rect.left(), min(pos.x(), viewport_rect.right())),
			max(viewport_rect.top(), min(pos.y(), viewport_rect.bottom()))
		)
		index = self.indexAt(pos)
		end_row = index.row() if index.isValid() else model.rowCount() - 1
		first_row, last_row = sorted((self._start_row, end_row))
		selection = QItemSelection(
			model.index(first_row, 0),
			model.index(last_row, model.columnCount() - 1)
		)
		if self._keep and self._snapshot is not None:
			selection.merge(self._snapshot, QISM.Select)
		self.selectionModel().select(
			selection, QISM.ClearAndSelect | QISM.Rows
		)
		self.selectionModel().setCurrentIndex(
			model.index(end_row, 0), QISM.NoUpdate
		)

	def _outside_scroll_axis(self, pos):
		bar = self._drag_selection_scroll_bar()
		if bar.orientation() == Qt.Vertical:
			return pos.y() < 0 or pos.y() >= self.viewport().height()
		return pos.x() < 0 or pos.x() >= self.viewport().width()

	def _auto_scroll(self):
		if not self._active or self._last_drag_pos is None:
			return
		pos = self.viewport().mapFromGlobal(QCursor.pos())
		if not self._outside_scroll_axis(pos):
			pos = self._last_drag_pos
			if not self._outside_scroll_axis(pos):
				return
		bar = self._drag_selection_scroll_bar()
		if bar.orientation() == Qt.Vertical:
			delta = -bar.singleStep() if pos.y() < 0 else bar.singleStep()
		else:
			delta = -bar.singleStep() if pos.x() < 0 else bar.singleStep()
		bar.setValue(bar.value() + delta)
		self._last_drag_pos = QPoint(pos)
		self._apply_range(pos)

	def _drag_selection_scroll_bar(self):
		return self.verticalScrollBar()

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.LeftButton:
			self._drag_selection_scroll_timer.stop()
			self._press_pos = None
			self._start_row = None
			self._keep = False
			self._snapshot = None
			self._active = False
			self._last_drag_pos = None
		super().mouseReleaseEvent(event)
