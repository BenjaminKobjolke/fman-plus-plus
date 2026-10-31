"""Show dialogs inside the main window, which modal dialogs lock (upstream #125)."""

from PyQt5.QtCore import QEvent, QEventLoop, QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication, QFrame
from PyQt5 import sip


def exec_in_window(dialog, parent):
	previous_focus = QApplication.focusWidget()
	dialog.setParent(parent, Qt.SubWindow)
	dialog.setAutoFillBackground(True)
	scrim = Scrim(parent)
	scrim.clicked.connect(dialog.reject)
	dialog.adjustSize()
	_position(dialog, parent)
	resize_filter = _ResizeFilter(parent, scrim, dialog)
	parent.installEventFilter(resize_filter)
	event_loop = QEventLoop()
	dialog.finished.connect(event_loop.quit)
	try:
		scrim.show()
		scrim.raise_()
		dialog.show()
		dialog.raise_()
		dialog.setFocus()
		event_loop.exec()
	finally:
		parent.removeEventFilter(resize_filter)
		scrim.close()
		if previous_focus is not None and not sip.isdeleted(previous_focus):
			previous_focus.setFocus()
	return dialog.result()


def _position(dialog, parent):
	dialog.move(
		max(0, (parent.width() - dialog.width()) // 2),
		max(0, (parent.height() - dialog.height()) // 2),
	)


class _ResizeFilter(QObject):
	def __init__(self, parent, scrim, dialog):
		super().__init__()
		self._parent = parent
		self._scrim = scrim
		self._dialog = dialog
	def eventFilter(self, watched, event):
		if watched is self._parent and event.type() == QEvent.Resize:
			self._scrim.setGeometry(self._parent.rect())
			_position(self._dialog, self._parent)
		return False


class Scrim(QFrame):
	"""
	Dims the main window while a dialog is open, so the dialog reads against the
	file list instead of competing with it. Its color - and thus how strong the
	dim is, in the alpha byte - is the theme's `scrim_bg`.
	"""

	clicked = pyqtSignal()

	def __init__(self, parent):
		super().__init__(parent)
		self.setFocusPolicy(Qt.NoFocus)
		self.setGeometry(parent.rect())
		self.raise_()
	def close(self):
		self.setParent(None)
	def mousePressEvent(self, event):
		self.clicked.emit()
