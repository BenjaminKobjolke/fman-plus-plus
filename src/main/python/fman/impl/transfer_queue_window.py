"""Window and status bar button for managing queued transfers."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
	QApplication, QDialog, QHBoxLayout, QListWidget, QListWidgetItem,
	QPushButton, QStyle, QToolButton, QVBoxLayout,
)


class TransferQueueWindow(QDialog):
	_entries_changed = pyqtSignal(object)

	def __init__(self, parent, queue):
		super().__init__(parent)
		self._queue = queue
		self.setWindowTitle('Transfer queue')
		self.setMinimumWidth(420)
		self._entries = QListWidget(self)
		self._entries.currentItemChanged.connect(self._update_controls)

		self._move_up = QPushButton('Move up', self)
		self._move_down = QPushButton('Move down', self)
		self._remove = QPushButton('Remove', self)
		self._close = QPushButton('Close', self)
		self._move_up.clicked.connect(lambda: self._move(-1))
		self._move_down.clicked.connect(lambda: self._move(1))
		self._remove.clicked.connect(self._remove_selected)
		self._close.clicked.connect(self.hide)

		controls = QHBoxLayout()
		for button in (self._move_up, self._move_down, self._remove, self._close):
			controls.addWidget(button)
		layout = QVBoxLayout(self)
		layout.addWidget(self._entries)
		layout.addLayout(controls)

		self._entries_changed.connect(self._refresh)
		queue.add_listener(self._entries_changed.emit)
		self._refresh(queue.entries())

	def show_queue(self):
		self.show()
		self.raise_()
		self.activateWindow()

	def _refresh(self, entries):
		selected = self._entries.currentItem()
		selected_id = selected.data(Qt.UserRole) if selected is not None else None
		self._entries.clear()
		selected_row = 0
		for row, entry in enumerate(entries):
			label = entry.title
			if entry.running:
				label += ' (Running)'
			item = QListWidgetItem(label)
			item.setData(Qt.UserRole, entry.id)
			self._entries.addItem(item)
			if entry.id == selected_id:
				selected_row = row
		if entries:
			self._entries.setCurrentRow(selected_row)
		self._update_controls()

	def _selected(self):
		item = self._entries.currentItem()
		if item is None:
			return None
		return item.data(Qt.UserRole), self._entries.currentRow()

	def _update_controls(self, *_):
		selected = self._selected()
		if selected is None:
			self._move_up.setEnabled(False)
			self._move_down.setEnabled(False)
			self._remove.setEnabled(False)
			return
		entry_id, row = selected
		entries = self._queue.entries()
		if row >= len(entries) or entries[row].id != entry_id:
			self._move_up.setEnabled(False)
			self._move_down.setEnabled(False)
			self._remove.setEnabled(False)
			return
		waiting = not entries[row].running
		self._move_up.setEnabled(waiting and row > 1)
		self._move_down.setEnabled(waiting and row < len(entries) - 1)
		self._remove.setEnabled(waiting)

	def _move(self, offset):
		selected = self._selected()
		if selected is None:
			return
		entry_id, _ = selected
		if offset < 0:
			self._queue.move_up(entry_id)
		else:
			self._queue.move_down(entry_id)

	def _remove_selected(self):
		selected = self._selected()
		if selected is not None:
			self._queue.remove(selected[0])


class TransferQueueButton(QToolButton):
	_entries_changed = pyqtSignal(object)
	show_queue_requested = pyqtSignal()

	def __init__(self, status_bar, queue, show_queue, show_status_message):
		super().__init__(status_bar)
		self._known_ids = set()
		self._show_status_message = show_status_message
		self.setToolButtonStyle(Qt.ToolButtonIconOnly)
		self.setAutoRaise(True)
		self.setToolTip('Transfer queue')
		self.setIcon(QApplication.style().standardIcon(
			QStyle.SP_FileDialogDetailedView))
		self.clicked.connect(show_queue)
		self._entries_changed.connect(self._refresh)
		status_bar.addPermanentWidget(self)
		queue.add_listener(self._entries_changed.emit)
		self._refresh(queue.entries())

	def _refresh(self, entries):
		ids = {entry.id for entry in entries}
		for entry in entries:
			if entry.id not in self._known_ids and not entry.running:
				self._show_status_message(
					'Transfer queued: {}'.format(entry.title), 3)
		self._known_ids = ids
		waiting = max(0, len(entries) - 1)
		self.setVisible(waiting > 0)
		if waiting:
			self.setToolTip('Transfer queue ({} waiting)'.format(waiting))
		else:
			self.setToolTip('Transfer queue')
