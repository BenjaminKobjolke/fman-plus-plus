"""Read and manage native Properties dialogs owned by fman."""

import os
from dataclasses import asdict, dataclass
from typing import Any

from PyQt5.QtCore import QBuffer, QIODevice, QRect
from PyQt5.QtWidgets import QApplication

from fman.impl.native_windows import (
	own_dialog_windows, pane_cursor_rects, screen_index_at,
)
from fman.impl.util.qt.thread import run_in_main_thread


def validate_window_position(payload: dict[str, Any]) -> dict[str, int]:
	values = {}
	for name, minimum, maximum in (
		('x', -100000, 100000), ('y', -100000, 100000), ('screen', 0, None),
	):
		if name not in payload:
			continue
		value = payload[name]
		if (not isinstance(value, int) or isinstance(value, bool)
			or value < minimum
			or maximum is not None and value > maximum):
			if maximum is None:
				raise ValueError('screen must be a non-negative integer.')
			raise ValueError('%s must be an integer from %s to %s.' % (
				name, minimum, maximum))
		values[name] = value
	if 'screen' in values and ('x' in values or 'y' in values):
		raise ValueError('screen cannot be combined with x or y.')
	return values


@dataclass(frozen=True)
class ScreenInfo:
	index: int
	geometry: dict
	available_geometry: dict
	primary: bool


@dataclass(frozen=True)
class NativeWindowInfo:
	handle: int
	title: str
	geometry: dict
	screen: int | None


@dataclass(frozen=True)
class PaneGeometry:
	geometry: dict | None
	cursor_row: dict | None


@dataclass(frozen=True)
class NativeSnapshot:
	screens: list[ScreenInfo]
	main_window: dict
	main_window_screen: int | None
	panes: list[PaneGeometry]
	windows: list[NativeWindowInfo]


def _rect(rect: QRect) -> dict[str, int]:
	return {
		'x': rect.x(), 'y': rect.y(),
		'width': rect.width(), 'height': rect.height(),
	}


class NativeReadout:
	def __init__(self, main_window: Any, plugin_support: Any) -> None:
		self._main_window = main_window
		self._plugin_support = plugin_support

	@run_in_main_thread
	def snapshot(self) -> dict[str, Any]:
		qt_screens = QApplication.screens()
		screens = [ScreenInfo(
			index, _rect(screen.geometry()), _rect(screen.availableGeometry()),
			screen is QApplication.primaryScreen(),
		) for index, screen in enumerate(qt_screens)]
		window_rect = self._main_window.frameGeometry()
		panes = []
		for pane in self._plugin_support.get_panes():
			try:
				pane_rect, row_rect = pane_cursor_rects(pane._widget)
			except AttributeError:
				panes.append(PaneGeometry(None, None))
			else:
				panes.append(PaneGeometry(
					_rect(pane_rect), _rect(row_rect) if row_rect else None,
				))
		windows = []
		if os.name == 'nt':
			import win32gui
			for handle in sorted(own_dialog_windows()):
				rect = win32gui.GetWindowRect(handle)
				geometry = _rect_from_edges(rect)
				windows.append(NativeWindowInfo(
					handle, win32gui.GetWindowText(handle), geometry,
					screen_index_at(QRect(
						rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]),
						qt_screens),
				))
		return asdict(NativeSnapshot(
			screens, _rect(window_rect), screen_index_at(window_rect, qt_screens),
			panes, windows,
		))

	@run_in_main_thread
	def close_all(self) -> int:
		if os.name != 'nt':
			return 0
		import win32con
		import win32gui
		windows = sorted(own_dialog_windows())
		for handle in windows:
			win32gui.PostMessage(handle, win32con.WM_CLOSE, 0, 0)
		return len(windows)

	@run_in_main_thread
	def screen_png(self) -> bytes:
		screen = self._main_window.screen() or QApplication.primaryScreen()
		if screen is None:
			return b''
		buffer = QBuffer()
		buffer.open(QIODevice.WriteOnly)
		screen.grabWindow(0).save(buffer, 'PNG')
		return bytes(buffer.data())


def _rect_from_edges(edges: tuple[int, int, int, int]) -> dict[str, int]:
	left, top, right, bottom = edges
	return {'x': left, 'y': top, 'width': right - left, 'height': bottom - top}
