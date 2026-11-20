"""Capture a window with its visible non-modal progress dialogs."""

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QProgressDialog, QWidget

from fman.impl.scripting.window_paint import compose_screen


def grab_with_progress_dialogs(window: QWidget) -> QPixmap:
	"""Grab a window and paint its visible non-modal progress dialogs over it."""
	# Progress dialogs are separate top-level windows, so the main window's
	# grab() never contains them.
	layers = [
		(QRect(widget.mapToGlobal(widget.rect().topLeft()), widget.size()),
		 widget.grab().toImage())
		for widget in QApplication.topLevelWidgets()
		if isinstance(widget, QProgressDialog)
		and widget is not window
		and widget.isVisible()
		and not widget.isModal()
		and widget.windowModality() == Qt.NonModal
	]
	return compose_screen(window.grab(), window.geometry(), layers)
