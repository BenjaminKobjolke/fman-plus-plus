"""Turn Ctrl-wheel movement into whole zoom steps."""

from PyQt5.QtCore import Qt


WHEEL_NOTCH = 120


class CtrlWheelZoom:
	"""Convert Ctrl-wheel angle deltas into whole zoom steps."""

	def __init__(self, on_zoom_step):
		self._on_zoom_step = on_zoom_step
		self._remainder = 0

	def handle(self, event):
		if not event.modifiers() & Qt.ControlModifier:
			self._remainder = 0
			return False
		delta = event.angleDelta().y()
		if not delta:
			return False
		self._remainder += delta
		while self._remainder >= WHEEL_NOTCH:
			self._on_zoom_step(1)
			self._remainder -= WHEEL_NOTCH
		while self._remainder <= -WHEEL_NOTCH:
			self._on_zoom_step(-1)
			self._remainder += WHEEL_NOTCH
		return True
