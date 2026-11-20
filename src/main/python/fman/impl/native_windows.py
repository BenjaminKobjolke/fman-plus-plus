"""Shared geometry and enumeration for native windows owned by fman."""

import os
from typing import Any, Sequence

from PyQt5.QtCore import QRect


_DIALOG_CLASS = '#32770'


def own_dialog_windows() -> set[int]:
	import win32gui
	import win32process

	windows = set()
	process_id = os.getpid()

	def collect(hwnd, _):
		if _is_own_window(hwnd, process_id, win32gui, win32process):
			if win32gui.GetClassName(hwnd) == _DIALOG_CLASS:
				windows.add(hwnd)

	win32gui.EnumWindows(collect, None)
	return windows


def own_windows_top_to_bottom(qt_hwnds: set[int]) -> list[int]:
	"""Return visible Qt windows and native dialogs in Windows stacking order."""
	import win32gui
	import win32process

	windows = []
	process_id = os.getpid()

	def collect(hwnd, _):
		if not _is_own_window(hwnd, process_id, win32gui, win32process):
			return
		if hwnd in qt_hwnds or win32gui.GetClassName(hwnd) == _DIALOG_CLASS:
			windows.append(hwnd)

	win32gui.EnumWindows(collect, None)
	return windows


def _is_own_window(hwnd, process_id, win32gui, win32process):
	if not win32gui.IsWindowVisible(hwnd):
		return False
	_, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
	return window_process_id == process_id


def pane_cursor_rects(widget: Any) -> tuple[QRect, QRect | None]:
	"""Return the pane and selected-row rectangles in global screen coordinates."""
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
				viewport.mapToGlobal(candidate.topLeft()), candidate.size())
	return pane_rect, row_rect


def screen_index_at(rect: QRect, screens: Sequence[Any]) -> int | None:
	"""Return the screen containing rect's center, or its nearest screen."""
	center = rect.center()
	geometries = [
		screen if isinstance(screen, QRect) else screen.geometry()
		for screen in screens
	]
	for index, geometry in enumerate(geometries):
		if geometry.contains(center):
			return index
	if not geometries:
		return None
	def distance(geometry):
		x = min(max(center.x(), geometry.left()), geometry.right())
		y = min(max(center.y(), geometry.top()), geometry.bottom())
		return (center.x() - x) ** 2 + (center.y() - y) ** 2
	return min(range(len(geometries)), key=lambda index: distance(geometries[index]))
