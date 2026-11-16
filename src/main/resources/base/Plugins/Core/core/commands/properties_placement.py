"""Move new Windows shell Properties dialogs beside the active pane selection."""

import time

import win32con
import win32gui
from PyQt5.QtCore import QPoint, QRect, QTimer
from PyQt5.QtWidgets import QApplication
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.native_windows import own_dialog_windows, pane_cursor_rects


_POLL_MS = 50
_TIMEOUT_MS = 3000
_CASCADE_PX = 30


def target_point(row_rect, pane_rect):
	if row_rect is None:
		return pane_rect.topLeft() + QPoint(40, 40)
	return row_rect.bottomLeft()


def clamp_to_screen(rect, available):
	x, y = rect.x(), rect.y()
	if rect.width() > available.width() or rect.height() > available.height():
		return available.topLeft()
	max_x = available.x() + available.width() - rect.width()
	max_y = available.y() + available.height() - rect.height()
	return QPoint(
		min(max(x, available.x()), max_x),
		min(max(y, available.y()), max_y),
	)


def _pane_placement(pane):
	try:
		widget = pane._widget
		pane_rect, row_rect = pane_cursor_rects(widget)
		point = target_point(row_rect, pane_rect)
		screen = QApplication.screenAt(point) or widget.screen()
		return point, screen.availableGeometry()
	except AttributeError:
		return None, None

# Pane commands run on a worker thread, but the timer needs the GUI thread's event loop.
class PropertiesPlacer:
	# Keep the Python receiver alive after the command's local reference is released.
	_active_placers = set()

	@run_in_main_thread
	def __init__(self, pane, expected):
		self._expected = expected
		self._target, self._screen = _pane_placement(pane)
		self._before = own_dialog_windows() if self._target is not None else set()
		self._moved = set()
		self._started_at = None
		try:
			parent = pane._widget
		except AttributeError:
			parent = None
		self._timer = QTimer(parent)
		self._timer.timeout.connect(self._poll)

	@run_in_main_thread
	def watch(self):
		if self._target is None or self._expected <= 0:
			return
		self._started_at = time.monotonic()
		self._active_placers.add(self)
		self._timer.start(_POLL_MS)

	def _stop(self):
		self._timer.stop()
		self._active_placers.discard(self)

	def _poll(self):
		for hwnd in sorted(own_dialog_windows() - self._before - self._moved):
			left, top, right, bottom = win32gui.GetWindowRect(hwnd)
			rect = QRect(
				self._target.x() + len(self._moved) * _CASCADE_PX,
				self._target.y() + len(self._moved) * _CASCADE_PX,
				right - left,
				bottom - top,
			)
			point = clamp_to_screen(rect, self._screen)
			win32gui.SetWindowPos(
				hwnd, 0, point.x(), point.y(), 0, 0,
				win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
			)
			self._moved.add(hwnd)
			if len(self._moved) >= self._expected:
				self._stop()
				return
		if (time.monotonic() - self._started_at) * 1000 >= _TIMEOUT_MS:
			self._stop()
