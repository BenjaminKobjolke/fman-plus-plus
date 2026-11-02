from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget


class EdgeGrip(QWidget):
	WIDTH = 6

	def __init__(self, dialog, side, resize_to, on_released):
		super().__init__(dialog)
		self._dialog = dialog
		self._side = side
		self._resize_to = resize_to
		self._on_released = on_released
		self._start_x = None
		self._start_width = None
		self.setCursor(Qt.SizeHorCursor)
		self.setMouseTracking(True)

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self._start_x = event.globalX()
			self._start_width = self._dialog.width()
			event.accept()
			return
		super().mousePressEvent(event)

	def mouseMoveEvent(self, event):
		if self._start_x is not None:
			delta = event.globalX() - self._start_x
			factor = -2 if self._side == 'left' else 2
			self._resize_to(self._start_width + factor * delta)
			event.accept()
			return
		super().mouseMoveEvent(event)

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.LeftButton and self._start_x is not None:
			self._start_x = None
			self._start_width = None
			self._on_released()
			event.accept()
			return
		super().mouseReleaseEvent(event)


def place_grips(dialog, grips):
	for side, grip in grips.items():
		x = 0 if side == 'left' else dialog.width() - grip.WIDTH
		grip.setGeometry(x, 0, grip.WIDTH, dialog.height())
		grip.raise_()
