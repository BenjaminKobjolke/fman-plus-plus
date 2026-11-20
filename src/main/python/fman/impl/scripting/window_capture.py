"""Capture a window with visible progress dialogs, including Windows frames."""

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QGuiApplication, QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QProgressDialog, QWidget

from fman.impl.scripting.window_paint import compose_screen, print_window_image


def _dialog_layer(widget: QWidget) -> tuple[QRect, QImage]:
	if QGuiApplication.platformName() == 'windows':
		image = print_window_image(int(widget.winId()))
		if image is not None:
			return widget.frameGeometry(), image
	return (
		QRect(widget.mapToGlobal(widget.rect().topLeft()), widget.size()),
		widget.grab().toImage(),
	)


def grab_with_progress_dialogs(window: QWidget) -> QPixmap:
	"""Paint visible progress dialogs over the window, including Windows frames."""
	# Progress dialogs are separate top-level windows, so the main window's
	# grab() never contains them.
	layers = [
		_dialog_layer(widget)
		for widget in QApplication.topLevelWidgets()
		if isinstance(widget, QProgressDialog)
		and widget is not window
		and widget.isVisible()
		and not widget.isModal()
		and widget.windowModality() == Qt.NonModal
	]
	return compose_screen(window.grab(), window.geometry(), layers)
