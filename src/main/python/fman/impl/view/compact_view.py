from fman.impl.util.qt import ToolTipRole, connect_once
from fman.impl.view import set_selection
from fman.impl.view.drag_and_drop import DragAndDrop
from fman.impl.view.right_button_selection import RightButtonSelection
from fman.impl.view.move_without_updating_selection import \
	MoveWithoutUpdatingSelection
from fman.impl.view.pane_surface import PaneSurface
from fman.impl.view.single_row_mode import SingleRowMode
from PyQt5.QtCore import QEvent, QItemSelection, QItemSelectionModel as QISM, \
	QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QListView, QToolTip


class CompactFileView(
	PaneSurface, SingleRowMode, MoveWithoutUpdatingSelection,
	RightButtonSelection, DragAndDrop,
	QListView
):
	"""A column-major filename view sharing a pane's file view model."""

	activated = pyqtSignal()

	def __init__(self, file_view, on_doubleclicked=None):
		super().__init__(file_view.parentWidget())
		self._file_view = file_view
		self.key_press_event_filter = file_view.key_press_event_filter
		self.wheel_event_filter = file_view.wheel_event_filter
		self.setIconSize(file_view.iconSize())
		self.setViewMode(self.ListMode)
		self.setFlow(self.TopToBottom)
		self.setWrapping(True)
		self.setResizeMode(self.Adjust)
		self.setMovement(self.Static)
		self.setUniformItemSizes(True)
		self.setWordWrap(False)
		self.setTabKeyNavigation(False)
		self.setEditTriggers(self.NoEditTriggers)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.setContextMenuPolicy(Qt.DefaultContextMenu)
		self._backgrounds = ()
		self._pane_index = 0
		self._loading_text = ''
		self._delegate = file_view._delegate
		self.add_delegate(self._delegate)
		if on_doubleclicked is not None:
			self.doubleClicked.connect(on_doubleclicked)
		self._grid_width_update_pending = False

	def _header(self):
		return None

	def setModel(self, model):
		old_model = self.model()
		if old_model is not None:
			old_model.rowsInserted.disconnect(self.schedule_grid_width)
			old_model.rowsRemoved.disconnect(self.schedule_grid_width)
			old_model.modelReset.disconnect(self.schedule_grid_width)
		super().setModel(model)
		if model is not None:
			model.rowsInserted.connect(self.schedule_grid_width)
			model.rowsRemoved.connect(self.schedule_grid_width)
			model.modelReset.connect(self.schedule_grid_width)
			self.schedule_grid_width()

	def schedule_grid_width(self, *_):
		if self._grid_width_update_pending:
			return
		self._grid_width_update_pending = True
		QTimer.singleShot(0, self._update_grid_width)

	def _update_grid_width(self):
		self._grid_width_update_pending = False
		self.set_grid_width()

	def set_grid_width(self, *_):
		model = self.model()
		if model is None:
			return
		metrics = self.fontMetrics()
		longest = max(
			(metrics.horizontalAdvance(str(model.data(model.index(row, 0))))
			 for row in range(model.rowCount())),
			default=0
		)
		width = min(
			self.viewport().width(),
			longest + self.iconSize().width() + 16
		)
		width = max(1, width)
		height = max(metrics.height(), self.iconSize().height()) + 6
		grid_size = QSize(width, height)
		if grid_size != self.gridSize():
			self.setGridSize(grid_size)

	def tooltip_text(self, index):
		if not index.isValid():
			return ''
		text = index.data(ToolTipRole)
		if not text:
			return ''
		text_width = self.fontMetrics().horizontalAdvance(
			str(index.data(Qt.DisplayRole))
		)
		available = self.gridSize().width() - self.iconSize().width() - 16
		return text if text_width > available else ''

	def viewportEvent(self, event):
		if event.type() == QEvent.ToolTip:
			index = self.indexAt(event.pos())
			QToolTip.showText(
				event.globalPos(), self.tooltip_text(index), self
			)
			return True
		return super().viewportEvent(event)

	def paintEvent(self, event):
		self._request_visible_rows()
		self._paint_backgrounds()
		super().paintEvent(event)
		if self._loading_text and not self.model().rowCount():
			self._paint_loading_text()

	def _request_visible_rows(self):
		if not self.model() or not self.model().rowCount():
			return
		rect = self.viewport().rect()
		grid = self.gridSize()
		rows = set()
		for x in range(0, rect.width(), max(1, grid.width())):
			for y in range(0, rect.height(), max(1, grid.height())):
				index = self.indexAt(QPoint(x + 1, y + 1))
				if index.isValid():
					rows.add(index.row())
		if rows:
			self._file_view.request_rows(sorted(rows))

	def contextMenuEvent(self, event):
		if self.swallows_mouse_context_menu(event):
			return
		self._file_view.show_context_menu(
			event, self.indexAt(event.pos()), 0
		)

	def _right_button_selection_on(self):
		return self._file_view._right_button_selection_on()

	def _show_context_menu_for(self, event, index):
		self._file_view.show_context_menu(event, index, 0)

	def keyPressEvent(self, event):
		if event.key() == Qt.Key_End and event.modifiers() & Qt.ShiftModifier:
			current = self.currentIndex()
			if current.isValid() and self.model().rowCount():
				last = self.model().index(self.model().rowCount() - 1, 0)
				selection = QItemSelection(
					self.model().index(min(current.row(), last.row()), 0),
					self.model().index(max(current.row(), last.row()), 0)
				)
				self.selectionModel().select(
					selection, QISM.Toggle | QISM.Rows
				)
				self.setCurrentIndex(last)
				return
		if not self.key_press_event_filter(event):
			super().keyPressEvent(event)

	def wheelEvent(self, event):
		if self.wheel_event_filter(event):
			event.accept()
		else:
			super().wheelEvent(event)

	def edit_name(self, file_url, selection_start=0, selection_end=None):
		def on_editor_shown(editor):
			set_selection(editor, selection_start, selection_end)
		connect_once(self._file_view._delegate.editor_shown, on_editor_shown)
		self.edit(self.model().find(file_url))

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self.set_grid_width()

	def focusInEvent(self, event):
		super().focusInEvent(event)
		self.activated.emit()
		self._repaint_if_focus_matters()

	def focusOutEvent(self, event):
		super().focusOutEvent(event)
		self._repaint_if_focus_matters()
