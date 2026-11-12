"""Small Windows helpers used by multi-window screenshot demos."""

import ctypes
import sys


def process_tree(root_pid, parent_by_pid):
	"""Return a process and every descendant listed in a parent map."""
	children_by_parent = {}
	for process_id, parent_id in parent_by_pid.items():
		children_by_parent.setdefault(parent_id, []).append(process_id)

	process_ids = {root_pid}
	pending = [root_pid]
	while pending:
		parent_id = pending.pop()
		for child_id in children_by_parent.get(parent_id, ()):
			if child_id not in process_ids:
				process_ids.add(child_id)
				pending.append(child_id)
	return process_ids


def _parent_by_pid():
	"""Read the current Windows process-to-parent mapping."""
	from ctypes import wintypes

	class ProcessEntry32W(ctypes.Structure):
		_fields_ = [
			('dwSize', wintypes.DWORD),
			('cntUsage', wintypes.DWORD),
			('th32ProcessID', wintypes.DWORD),
			('th32DefaultHeapID', ctypes.c_size_t),
			('th32ModuleID', wintypes.DWORD),
			('cntThreads', wintypes.DWORD),
			('th32ParentProcessID', wintypes.DWORD),
			('pcPriClassBase', wintypes.LONG),
			('dwFlags', wintypes.DWORD),
			('szExeFile', wintypes.WCHAR * 260),
		]

	kernel32 = ctypes.windll.kernel32
	kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
	kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
	kernel32.Process32FirstW.argtypes = [
		wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W),
	]
	kernel32.Process32FirstW.restype = wintypes.BOOL
	kernel32.Process32NextW.argtypes = [
		wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W),
	]
	kernel32.Process32NextW.restype = wintypes.BOOL
	kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
	kernel32.CloseHandle.restype = wintypes.BOOL

	process_snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
	if process_snapshot == wintypes.HANDLE(-1).value:
		return {}

	parent_by_pid = {}
	try:
		entry = ProcessEntry32W()
		entry.dwSize = ctypes.sizeof(entry)
		if kernel32.Process32FirstW(process_snapshot, ctypes.byref(entry)):
			while True:
				parent_by_pid[entry.th32ProcessID] = entry.th32ParentProcessID
				if not kernel32.Process32NextW(
					process_snapshot, ctypes.byref(entry),
				):
					break
	finally:
		kernel32.CloseHandle(process_snapshot)
	return parent_by_pid


def foreground_process_window(process_id: int, title_part: str) -> int | None:
	"""Restore and foreground a visible top-level window owned by a process."""
	if sys.platform != 'win32':
		return None

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
	user32.GetWindowTextW.argtypes = [
		wintypes.HWND, wintypes.LPWSTR, ctypes.c_int,
	]
	user32.GetWindowTextW.restype = ctypes.c_int
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

	# The venv python.exe is a launcher; the window belongs to its child process.
	process_ids = process_tree(process_id, _parent_by_pid())

	def visit(hwnd, _):
		window_process_id = wintypes.DWORD()
		user32.GetWindowThreadProcessId(
			hwnd, ctypes.byref(window_process_id),
		)
		if (
			user32.IsWindowVisible(hwnd)
			and window_process_id.value in process_ids
		):
			title = ctypes.create_unicode_buffer(512)
			user32.GetWindowTextW(hwnd, title, len(title))
			if title_part in title.value:
				windows.append(hwnd)
		return True

	callback = callback_type(visit)
	user32.EnumWindows(callback, 0)
	if not windows:
		return None

	hwnd = windows[0]
	user32.AllowSetForegroundWindow(process_id)
	user32.ShowWindow(hwnd, 9)  # SW_RESTORE also shows a normal window.
	user32.BringWindowToTop(hwnd)
	user32.SetForegroundWindow(hwnd)
	if user32.GetForegroundWindow() == hwnd:
		return int(hwnd)

	foreground = user32.GetForegroundWindow()
	foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
	current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
	if not user32.AttachThreadInput(current_thread, foreground_thread, True):
		return None
	try:
		user32.BringWindowToTop(hwnd)
		user32.SetForegroundWindow(hwnd)
		return int(hwnd) if user32.GetForegroundWindow() == hwnd else None
	finally:
		user32.AttachThreadInput(current_thread, foreground_thread, False)
