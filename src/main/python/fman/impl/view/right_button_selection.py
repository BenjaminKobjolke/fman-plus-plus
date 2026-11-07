"""Right-button selection and delayed context menus for file views."""

from PyQt5.QtCore import QItemSelection, QItemSelectionModel as QISM, QTimer, Qt
from PyQt5.QtGui import QContextMenuEvent, QCursor

HOLD_FOR_CONTEXT_MENU_MS = 1000


class RightButtonSelection:
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._right_button_selection = False
		self._right_button_selection_start = None
		self._right_button_selection_last = None
		self._right_button_selection_state = False
		self._hold_timer = QTimer(self)
		self._hold_timer.setSingleShot(True)
		self._hold_timer.setInterval(HOLD_FOR_CONTEXT_MENU_MS)
		self._hold_timer.timeout.connect(self._open_hold_menu)

	def set_right_button_selection(self, enabled):
		self._right_button_selection = enabled

	def _right_button_selection_on(self):
		return self._right_button_selection

	def mousePressEvent(self, event):
		index = self.indexAt(event.pos())
		if self._right_button_selection_on() and \
			event.button() == Qt.RightButton and index.isValid():
			self.setFocus()
			selection = self.selectionModel()
			selection.setCurrentIndex(index, QISM.NoUpdate)
			selection.select(index, QISM.Toggle | QISM.Rows)
			self._right_button_selection_start = index
			self._right_button_selection_last = index
			self._right_button_selection_state = selection.isSelected(index)
			self._hold_timer.start()
			return
		super().mousePressEvent(event)

	def mouseMoveEvent(self, event):
		start = self._right_button_selection_start
		if event.buttons() & Qt.RightButton and start is not None:
			index = self.indexAt(event.pos())
			if index != start:
				self._hold_timer.stop()
			if index.isValid() and index != self._right_button_selection_last:
				last = self._right_button_selection_last
				first_row, last_row = sorted((last.row(), index.row()))
				model = self.model()
				selection = QItemSelection(
					model.index(first_row, 0),
					model.index(last_row, model.columnCount() - 1)
				)
				action = QISM.Select if self._right_button_selection_state \
					else QISM.Deselect
				self.selectionModel().select(selection, action | QISM.Rows)
				self.selectionModel().setCurrentIndex(index, QISM.NoUpdate)
				self._right_button_selection_last = index
			# shortcut: no auto-scroll while right-dragging; add it when a
			# long-list drag is requested
			return
		super().mouseMoveEvent(event)

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.RightButton and \
			self._right_button_selection_start is not None:
			self._hold_timer.stop()
			self._clear_right_button_drag()
			return
		super().mouseReleaseEvent(event)

	def swallows_mouse_context_menu(self, event):
		return self._right_button_selection_on() and \
			event.reason() == QContextMenuEvent.Mouse and \
			self.indexAt(event.pos()).isValid()

	def _open_hold_menu(self):
		start = self._right_button_selection_start
		if start is None:
			return
		self.selectionModel().select(start, QISM.Select | QISM.Rows)
		self._clear_right_button_drag()
		pos = self.viewport().mapFromGlobal(QCursor.pos())
		index = self.indexAt(pos)
		if not index.isValid():
			index = start
		global_pos = self.viewport().mapToGlobal(pos)
		event = QContextMenuEvent(QContextMenuEvent.Mouse, pos, global_pos)
		self._show_context_menu_for(event, index)

	def _clear_right_button_drag(self):
		self._right_button_selection_start = None
		self._right_button_selection_last = None
