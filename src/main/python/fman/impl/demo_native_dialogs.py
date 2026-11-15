"""Native shell dialogs used by demos and the screenshot recorder.

The recorder pins fman topmost, so unowned shell dialogs sort below it unless
the demo raises them before capturing a still.
"""

import logging
import os

try:
	import win32api
	import win32con
	import win32gui
	import win32process
except ImportError:
	win32api = win32con = win32gui = win32process = None

_DIALOG_CLASS = '#32770'
_WM_CLOSE = 0x0010


def own_native_dialogs():
	"""Return visible shell dialogs owned by this process."""
	if any(
		module is None for module in (win32gui, win32process)
	):
		logging.getLogger(__name__).warning(
			'Cannot access native demo dialogs because pywin32 is unavailable.'
		)
		return []

	process_id = os.getpid()
	dialogs = []

	def collect_own_dialog(hwnd, _):
		if not win32gui.IsWindowVisible(hwnd):
			return
		if win32gui.GetClassName(hwnd) != _DIALOG_CLASS:
			return
		_, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
		if window_process_id == process_id:
			dialogs.append(hwnd)

	win32gui.EnumWindows(collect_own_dialog, None)
	return dialogs


def close_native_dialogs():
	"""Close visible shell dialogs owned by this process."""
	if win32api is None:
		logging.getLogger(__name__).warning(
			'Cannot close native demo dialogs because pywin32 is unavailable.'
		)
		return
	for hwnd in own_native_dialogs():
		win32api.PostMessage(hwnd, _WM_CLOSE, 0, 0)


def raise_native_dialogs():
	"""Lift this process's shell dialogs above the pinned demo window."""
	if win32con is None or win32gui is None:
		# own_native_dialogs logs the shared pywin32-unavailable warning.
		own_native_dialogs()
		return
	dialogs = own_native_dialogs()
	flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
	for hwnd in dialogs:
		win32gui.SetWindowPos(
			hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, flags,
		)
	logging.getLogger(__name__).info(
			'Raised %d native demo dialog(s) above the demo window.', len(dialogs),
	)
