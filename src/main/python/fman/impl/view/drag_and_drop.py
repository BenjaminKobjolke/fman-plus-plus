from fbs_runtime.platform import is_mac, is_windows, is_linux
from fman.impl.util.qt import MoveAction, NoButton, AltModifier, \
	ControlModifier, CopyAction, get_urls
from fman.impl.drop_action import choose_drop_action
from PyQt5.QtCore import QItemSelectionModel as QISM
from PyQt5.QtWidgets import QAbstractItemView

class DragAndDrop:

	_IDLE_STATES = (QAbstractItemView.NoState, QAbstractItemView.AnimatingState)

	def __init__(self, parent=None):
		super().__init__(parent)
		self._dragged_index = None
		self.setDragEnabled(True)
		self.setDragDropMode(self.DragDrop)
		self.setDefaultDropAction(MoveAction)
		self.setDropIndicatorShown(True)
		self.setAcceptDrops(True)
		# Consider:
		#   A/
		#   B/
		# Drag A/ downwards. With dragDropOverwriteMode = False, as you leave A/
		# but before you reach B/, Qt draws a horizontal line between A/ and B/,
		# presumably to let you drag items to between rows. This may make sense
		# for other widgets, but we don't want it. We therefore set
		# dragDropOverwriteMode to True:
		self.setDragDropOverwriteMode(True)
	def mouseMoveEvent(self, event):
		if event.buttons() != NoButton and self.state() in self._IDLE_STATES:
			self._dragged_index = self.indexAt(event.pos())
			if self._dragged_index.isValid():
				# Qt's default implementation only starts dragging when there
				# are selected items. We also want to start dragging when there
				# aren't (because in this case we drag the focus item):
				self.setState(self.DraggingState)
				# startDrag(...) below now initiates drag and drop.
				return
		else:
			super().mouseMoveEvent(event)
	def startDrag(self, supportedActions):
		if not self._dragged_index or not self._dragged_index.isValid():
			return
		if self._dragged_index in self.selectedIndexes():
			super().startDrag(supportedActions)
		else:
			# The default implementation of Qt only supports dragging the
			# currently selected item(s). We therefore briefly need to "select"
			# the items we wish to drag. This has the (unintended) side-effect
			# that the dragged items are also rendered as being selected.
			selection = self.selectionModel().selection()
			current = self.selectionModel().currentIndex()
			try:
				self.selectionModel().clear()
				# When dragging items that have actually been selected by the
				# user, the cursor is on one of the selected items (because the
				# user clicked on it when initiating the drag). Mimic the same
				# behaviour for consistency:
				self.setCurrentIndex(self._dragged_index)
				self.selectionModel().select(
					self._dragged_index, QISM.ClearAndSelect | QISM.Rows
				)
				super().startDrag(supportedActions)
			finally:
				self.selectionModel().select(selection, QISM.ClearAndSelect)
				self.selectionModel().setCurrentIndex(current, QISM.NoUpdate)
	def _windows_drop_action(self, event):
		urls = get_urls(event.mimeData())
		dest = self.model().drop_dest_url(self.indexAt(event.pos()))
		return choose_drop_action(event.keyboardModifiers(), urls, dest)
	def dragEnterEvent(self, event):
		if not is_windows():
			return super().dragEnterEvent(event)
		action = self._windows_drop_action(event)
		if not event.possibleActions() & action:
			return super().dragEnterEvent(event)
		event.setDropAction(action)
		super().dragEnterEvent(event)
		if event.isAccepted():
			event.setDropAction(action)
			event.accept()
	def dragMoveEvent(self, event):
		if not is_windows():
			return super().dragMoveEvent(event)
		action = self._windows_drop_action(event)
		if not event.possibleActions() & action:
			return super().dragMoveEvent(event)
		event.setDropAction(action)
		super().dragMoveEvent(event)
		if event.isAccepted():
			event.setDropAction(action)
			event.accept()
	def dropEvent(self, event):
		modifiers = event.keyboardModifiers()
		if is_mac():
			do_copy = modifiers & AltModifier
		elif is_linux():
			do_copy = (modifiers & ControlModifier) or (modifiers & AltModifier)
		else:
			# Windows
			action = self._windows_drop_action(event)
		if not is_windows():
			action = CopyAction if do_copy else MoveAction
		event.setDropAction(action)
		super().dropEvent(event)
		if action == MoveAction and is_windows():
			# If we accept the event (which super().dropEvent(...) does above),
			# then Windows moves the file to the Recycle Bin!!! Avoid this:
			event.ignore()
