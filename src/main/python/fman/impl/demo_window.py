"""Small Windows helpers used by multi-window screenshot demos."""

import ctypes
import sys


def foreground_process_window(process_id):
	"""Restore and foreground a visible top-level window owned by a process."""
	if sys.platform != 'win32':
		return False

	from ctypes import wintypes

	user32 = ctypes.windll.user32
	windows = []
	callback_type = ctypes.WINFUNCTYPE(
		wintypes.BOOL, wintypes.HWND, wintypes.LPARAM,
	)
	user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
	user32.EnumWindows.restype = wintypes.BOOL
	user32.GetWindowThreadProcessId.argtypes = [
		wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
	]
	user32.GetWindowThreadProcessId.restype = wintypes.DWORD
	user32.IsWindowVisible.argtypes = [wintypes.HWND]
	user32.IsWindowVisible.restype = wintypes.BOOL
	user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
	user32.ShowWindow.restype = wintypes.BOOL
	user32.SetForegroundWindow.argtypes = [wintypes.HWND]
	user32.SetForegroundWindow.restype = wintypes.BOOL
	user32.BringWindowToTop.argtypes = [wintypes.HWND]
	user32.BringWindowToTop.restype = wintypes.BOOL
	user32.AttachThreadInput.argtypes = [
		wintypes.DWORD, wintypes.DWORD, wintypes.BOOL,
	]
	user32.AttachThreadInput.restype = wintypes.BOOL
	user32.GetForegroundWindow.restype = wintypes.HWND

	def visit(hwnd, _):
		window_process_id = wintypes.DWORD()
		user32.GetWindowThreadProcessId(
			hwnd, ctypes.byref(window_process_id),
		)
		if user32.IsWindowVisible(hwnd) and window_process_id.value == process_id:
			windows.append(hwnd)
		return True

	callback = callback_type(visit)
	user32.EnumWindows(callback, 0)
	if not windows:
		return False

	hwnd = windows[0]
	user32.AllowSetForegroundWindow(process_id)
	user32.ShowWindow(hwnd, 9)  # SW_RESTORE also shows a normal window.
	user32.BringWindowToTop(hwnd)
	user32.SetForegroundWindow(hwnd)
	if user32.GetForegroundWindow() == hwnd:
		return True

	foreground = user32.GetForegroundWindow()
	foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
	current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
	if not user32.AttachThreadInput(current_thread, foreground_thread, True):
		return False
	try:
		user32.BringWindowToTop(hwnd)
		user32.SetForegroundWindow(hwnd)
		return user32.GetForegroundWindow() == hwnd
	finally:
		user32.AttachThreadInput(current_thread, foreground_thread, False)
