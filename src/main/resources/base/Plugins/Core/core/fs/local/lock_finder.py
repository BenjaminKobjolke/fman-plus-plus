"""Find Windows processes that hold files open or work inside selected folders."""
import ctypes
from ctypes import wintypes
from collections import namedtuple
import os
from typing import Sequence

import psutil

from fman import PLATFORM


LockingProcess = namedtuple('LockingProcess', ('pid', 'name', 'reason'))
REASON_OPEN_FILE = 'has a file open'
REASON_WORKING_DIR = 'has its working directory inside'
ERROR_MORE_DATA = 234
_RM_SESSION_KEY_LENGTH = 32


class _RM_UNIQUE_PROCESS(ctypes.Structure):
	_fields_ = [
		('dwProcessId', wintypes.DWORD),
		('ProcessStartTime', wintypes.FILETIME),
	]


class _RM_PROCESS_INFO(ctypes.Structure):
	_fields_ = [
		('Process', _RM_UNIQUE_PROCESS),
		('strAppName', wintypes.WCHAR * 256),
		('strServiceShortName', wintypes.WCHAR * 64),
		('ApplicationType', wintypes.DWORD),
		('AppStatus', wintypes.DWORD),
		('TSSessionId', wintypes.DWORD),
		('bRestartable', wintypes.BOOL),
	]


def list_files(paths: Sequence[str]) -> list[str]:
	"""Return selected files and every file found below selected directories."""
	files = []
	seen = set()
	for path in paths:
		if os.path.isdir(path):
			for root, _, names in os.walk(path):
				for name in names:
					file_path = os.path.join(root, name)
					if file_path not in seen:
						files.append(file_path)
						seen.add(file_path)
		elif path not in seen:
			files.append(path)
			seen.add(path)
	return files


def find_locking_processes(
	paths: Sequence[str], files: Sequence[str]
) -> list[LockingProcess]:
	"""Find processes holding any selected file or working inside a selected folder."""
	if PLATFORM != 'Windows':
		return []
	processes = _restart_manager(files)
	directories = [path for path in paths if os.path.isdir(path)]
	processes.extend(_working_dirs(directories))
	unique = {(process.pid, process.reason): process for process in processes}
	return sorted(
		unique.values(),
		key=lambda process: (process.name or '').casefold(),
	)


def _restart_manager(files: Sequence[str]) -> list[LockingProcess]:
	if not files:
		return []
	rstrtmgr = ctypes.WinDLL('rstrtmgr', use_last_error=True)
	start_session = rstrtmgr.RmStartSession
	start_session.argtypes = (
		ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, wintypes.LPWSTR
	)
	start_session.restype = wintypes.DWORD
	register_resources = rstrtmgr.RmRegisterResources
	register_resources.argtypes = (
		wintypes.DWORD, wintypes.UINT, ctypes.POINTER(wintypes.LPCWSTR),
		wintypes.UINT, ctypes.POINTER(_RM_UNIQUE_PROCESS),
		wintypes.UINT, ctypes.POINTER(wintypes.LPCWSTR),
	)
	register_resources.restype = wintypes.DWORD
	get_list = rstrtmgr.RmGetList
	get_list.argtypes = (
		wintypes.DWORD, ctypes.POINTER(wintypes.UINT),
		ctypes.POINTER(wintypes.UINT), ctypes.POINTER(_RM_PROCESS_INFO),
		ctypes.POINTER(wintypes.DWORD),
	)
	get_list.restype = wintypes.DWORD
	end_session = rstrtmgr.RmEndSession
	end_session.argtypes = (wintypes.DWORD,)
	end_session.restype = wintypes.DWORD

	session_handle = wintypes.DWORD()
	session_key = ctypes.create_unicode_buffer(_RM_SESSION_KEY_LENGTH + 1)
	_result_or_raise(
		start_session(ctypes.byref(session_handle), 0, session_key)
	)
	try:
		resource_array = (wintypes.LPCWSTR * len(files))(*files)
		_result_or_raise(register_resources(
			session_handle, len(files), resource_array, 0, None, 0, None
		))
		return _get_restart_manager_processes(get_list, session_handle)
	finally:
		end_session(session_handle)


def _get_restart_manager_processes(get_list, session_handle):
	needed = wintypes.UINT()
	count = wintypes.UINT()
	reboot_reasons = wintypes.DWORD()
	error = get_list(
		session_handle, ctypes.byref(needed), ctypes.byref(count), None,
		ctypes.byref(reboot_reasons)
	)
	if error == 0:
		return []
	if error != ERROR_MORE_DATA:
		_result_or_raise(error)
	while True:
		count.value = needed.value
		process_array = (_RM_PROCESS_INFO * count.value)()
		error = get_list(
			session_handle, ctypes.byref(needed), ctypes.byref(count),
			process_array, ctypes.byref(reboot_reasons)
		)
		if error == ERROR_MORE_DATA:
			continue
		_result_or_raise(error)
		return [
			LockingProcess(
				process.Process.dwProcessId,
				process.strAppName,
				REASON_OPEN_FILE,
			)
			for process in process_array[:count.value]
		]


def _working_dirs(dirs: Sequence[str]) -> list[LockingProcess]:
	normalized_dirs = [os.path.normcase(os.path.abspath(path)) for path in dirs]
	processes = []
	for process in psutil.process_iter(['pid', 'name']):
		try:
			cwd = os.path.normcase(os.path.abspath(process.cwd()))
		except (psutil.AccessDenied, psutil.NoSuchProcess):
			continue
		for directory in normalized_dirs:
			try:
				matches = os.path.commonpath((directory, cwd)) == directory
			except ValueError:
				matches = False
			if matches:
				pid = process.info['pid']
				processes.append(LockingProcess(
					pid, process.info['name'] or str(pid), REASON_WORKING_DIR
				))
				break
	return processes


def _result_or_raise(error_code: int) -> None:
	if error_code:
		raise OSError(error_code, ctypes.FormatError(error_code))
