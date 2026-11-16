"""Render background-launched fman's covered windows into desktop screenshots."""

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QImage, QPainter, QPixmap


def print_window_image(hwnd: int) -> QImage | None:
	"""Capture a window's own contents without raising it on the desktop."""
	import ctypes
	import win32gui
	import win32ui
	from PyQt5.QtWinExtras import QtWin

	left, top, right, bottom = win32gui.GetWindowRect(hwnd)
	width, height = right - left, bottom - top
	if width <= 0 or height <= 0:
		return None

	window_dc = win32gui.GetWindowDC(hwnd)
	if not window_dc:
		return None
	memory_dc = None
	bitmap = None
	try:
		source_dc = win32ui.CreateDCFromHandle(window_dc)
		memory_dc = source_dc.CreateCompatibleDC()
		bitmap = win32ui.CreateBitmap()
		bitmap.CreateCompatibleBitmap(source_dc, width, height)
		memory_dc.SelectObject(bitmap)
		print_window = ctypes.windll.user32.PrintWindow
		print_window.argtypes = [
			ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
		]
		print_window.restype = ctypes.c_int
		captured = print_window(hwnd, memory_dc.GetSafeHdc(), 2)
		if not captured:
			return None
		return QtWin.fromHBITMAP(bitmap.GetHandle()).toImage()
	finally:
		if memory_dc is not None:
			memory_dc.DeleteDC()
		if bitmap is not None:
			win32gui.DeleteObject(bitmap.GetHandle())
		win32gui.ReleaseDC(hwnd, window_dc)


def compose_screen(
		background: QPixmap, screen_rect: QRect,
		layers: list[tuple[QRect, QImage]]) -> QPixmap:
	"""Paint window images over a screen capture, in bottom-to-top order."""
	result = QPixmap(background)
	painter = QPainter(result)
	try:
		for rect, image in layers:
			painter.drawImage(rect.topLeft() - screen_rect.topLeft(), image)
	finally:
		painter.end()
	return result
