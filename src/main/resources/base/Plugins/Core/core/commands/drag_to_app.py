"""Hand selected local files to windrop, aimed at one of the last five apps.

A drag fman fakes with DoDragDrop (no mouse button held) is rejected by many
apps. windrop (github.com/BenjaminKobjolke/windrop) shows a small card at the
cursor that the user drags from with the real mouse, so fman only focuses the
target, puts the cursor on its center and launches windrop there.
"""
from fman import (
	DirectoryPaneCommand, QuicksearchItem, show_alert, show_quicksearch
)
from fbs_runtime.platform import is_windows
from fman.url import as_human_readable, splitscheme

from collections import namedtuple
from core.settings import SETTINGS_FILE, get_setting

import ctypes
import ctypes.wintypes
import os
import subprocess

__all__ = ['DragToLastUsedApp']

_Window = namedtuple(
	'_Window',
	'hwnd pid title visible minimized tool_window cloaked topmost'
)
_WINDROP_SETTING = 'windrop_path'
# Vendored by tools/update_windrop.bat, next to 7z.exe (see core/fs/zip.py).
_BUNDLED_WINDROP = os.path.join(
	os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
	'bin', 'windows', 'windrop.exe'
)


class DragToLastUsedApp(DirectoryPaneCommand):
	"""Pick a recent app and open windrop on its center for the files."""

	aliases = 'Drag to last used app',

	def is_visible(self):
		return is_windows()

	def __call__(self):
		cursor = self.pane.get_file_under_cursor()
		chosen = self.pane.get_selected_files() or \
		         ([cursor] if cursor else [])
		if not chosen:
			return
		if any(splitscheme(url)[0] != 'file://' for url in chosen):
			show_alert('Drag to last used app only supports local files.')
			return
		windrop = _find_windrop()
		if windrop is None:
			show_alert(
				'windrop.exe not found at %s. Run tools/update_windrop.bat or '
				'set "%s" in %s.' % (_BUNDLED_WINDROP, _WINDROP_SETTING, SETTINGS_FILE)
			)
			return
		paths = [as_human_readable(url) for url in chosen]
		targets = _pick_targets(_enumerate_windows(), os.getpid())
		if not targets:
			show_alert('No other app window found.')
			return
		main_window = self.pane.window._widget
		target = _choose_target(targets, len(paths))
		if target is None:
			main_window.raise_()
			main_window.activateWindow()
			return
		hwnd = target.hwnd
		import win32api
		import win32gui
		win32gui.SetForegroundWindow(hwnd)
		left, top, right, bottom = win32gui.GetWindowRect(hwnd)
		# windrop opens its card at the cursor.
		win32api.SetCursorPos(((left + right) // 2, (top + bottom) // 2))
		# windrop owns the drag, cancel and result from here; don't wait on it.
		subprocess.Popen(
			_windrop_command(windrop, paths),
			creationflags=subprocess.CREATE_NO_WINDOW
		)


def _find_windrop():
	# The setting overrides the bundled exe, e.g. to try a fresh windrop build.
	configured = get_setting(SETTINGS_FILE, _WINDROP_SETTING)
	if configured and os.path.isfile(configured):
		return configured
	return _BUNDLED_WINDROP if os.path.isfile(_BUNDLED_WINDROP) else None


def _windrop_command(windrop, paths):
	# The user already chose the target, so windrop engages the drag at
	# once and the keyboard steers it.
	return [windrop, '--keyboard', *paths]


def _choose_target(targets, file_count):
	file_word = 'file' if file_count == 1 else 'files'
	description = (
		'Drag %d %s to the selected app\n\n' % (file_count, file_word) +
		'WASD / arrow keys: move the cursor (hold to keep moving)\n'
		'Q / Space / Enter: drop the files\n'
		'Esc: cancel\n'
		'Moving the real mouse and clicking also drops.'
	)
	items = [
		(window, _get_exe_name(window.pid)) for window in targets
	]

	def get_items(query):
		query = query.lower()
		return (
			QuicksearchItem(
				window, title=window.title, hint=exe, description=description
			)
			for window, exe in items
			if query in window.title.lower() or query in exe.lower()
		)
	result = show_quicksearch(get_items)
	return result[1] if result else None


def _get_exe_name(pid):
	try:
		kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
		open_process = kernel32.OpenProcess
		open_process.argtypes = (ctypes.wintypes.DWORD, ctypes.wintypes.BOOL,
		                         ctypes.wintypes.DWORD)
		open_process.restype = ctypes.wintypes.HANDLE
		handle = open_process(0x1000, False, pid)
		if not handle:
			return ''
		try:
			query_image = kernel32.QueryFullProcessImageNameW
			query_image.argtypes = (
				ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD,
				ctypes.wintypes.LPWSTR, ctypes.POINTER(ctypes.wintypes.DWORD)
			)
			query_image.restype = ctypes.wintypes.BOOL
			path = ctypes.create_unicode_buffer(32768)
			length = ctypes.wintypes.DWORD(len(path))
			if not query_image(handle, 0, path, ctypes.byref(length)):
				return ''
			return os.path.basename(path.value)
		finally:
			kernel32.CloseHandle(handle)
	except Exception:
		return ''


def _get_window_pid(hwnd):
	user32 = ctypes.WinDLL('user32', use_last_error=True)
	get_window_thread_process_id = user32.GetWindowThreadProcessId
	get_window_thread_process_id.argtypes = (
		ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)
	)
	get_window_thread_process_id.restype = ctypes.wintypes.DWORD
	pid = ctypes.wintypes.DWORD()
	get_window_thread_process_id(hwnd, ctypes.byref(pid))
	return pid.value


def _enumerate_windows():
	import win32con
	import win32gui

	windows = []

	def collect(hwnd, _):
		try:
			pid = _get_window_pid(hwnd)
			ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
			windows.append(_Window(
				hwnd,
				pid,
				win32gui.GetWindowText(hwnd),
				bool(win32gui.IsWindowVisible(hwnd)),
				bool(win32gui.IsIconic(hwnd)),
				bool(ex_style & win32con.WS_EX_TOOLWINDOW),
				_is_cloaked(hwnd),
				bool(ex_style & win32con.WS_EX_TOPMOST),
			))
		except Exception:
			# A window can disappear while EnumWindows is walking the Z-order.
			pass
		return True

	win32gui.EnumWindows(collect, None)
	return windows


def _is_cloaked(hwnd):
	try:
		cloaked = ctypes.c_int()
		result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
			hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
		)
		return result == 0 and bool(cloaked.value)
	except (AttributeError, OSError):
		return False


def _pick_targets(windows, own_pid, limit=5):
	eligible = []
	for window in windows:
		# ponytail: skip minimized windows until restore-and-confirm support exists.
		if window.minimized:
			continue
		if (window.visible and not window.tool_window and not window.cloaked and
				window.title and window.pid != own_pid):
			eligible.append(window)
	normal = [window for window in eligible if not window.topmost]
	topmost = [window for window in eligible if window.topmost]
	return (normal + topmost)[:limit]
