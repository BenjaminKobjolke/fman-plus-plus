"""Move new Windows shell Properties dialogs beside the active pane selection."""

import os
import time

import win32con
import win32gui
import win32process
from PyQt5.QtCore import QPoint, QRect, QTimer
from PyQt5.QtWidgets import QApplication


_POLL_MS = 50
_TIMEOUT_MS = 3000
_CASCADE_PX = 30
_DIALOG_CLASS = '#32770'


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


def own_dialog_windows():
	windows = set()
	process_id = os.getpid()

	def collect(hwnd, _):
		if not win32gui.IsWindowVisible(hwnd):
			return
		if win32gui.GetClassName(hwnd) != _DIALOG_CLASS:
			return
		_, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
		if window_process_id == process_id:
			windows.add(hwnd)

	win32gui.EnumWindows(collect, None)
	return windows


def _pane_placement(pane):
	try:
		widget = pane._widget
		widget_rect = widget.rect()
		pane_rect = QRect(widget.mapToGlobal(widget_rect.topLeft()), widget_rect.size())
		row_rect = None
		view = widget._view_mode.visible_view()
		if view is not None:
			index = view.currentIndex()
			viewport = view.viewport()
			candidate = view.visualRect(index)
			if index.isValid() and candidate.intersects(viewport.rect()):
				row_rect = QRect(
					viewport.mapToGlobal(candidate.topLeft()), candidate.size()
				)
		point = target_point(row_rect, pane_rect)
		screen = QApplication.screenAt(point) or widget.screen()
		return point, screen.availableGeometry()
	except AttributeError:
		return None, None


class PropertiesPlacer:
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

	def watch(self):
		if self._target is None or self._expected <= 0:
			return
		self._started_at = time.monotonic()
		self._timer.start(_POLL_MS)

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
				self._timer.stop()
				return
		if (time.monotonic() - self._started_at) * 1000 >= _TIMEOUT_MS:
			self._timer.stop()
