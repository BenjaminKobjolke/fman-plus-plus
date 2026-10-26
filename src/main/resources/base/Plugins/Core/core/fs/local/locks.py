"""Check whether Windows will allow a local file to be moved or replaced.

The check runs immediately before each file operation. Scanning a whole tree
up front would add latency and still miss files locked after the scan.
"""
import ctypes
import errno
from ctypes import wintypes

from fman import PLATFORM

from core.settings import get_setting, SETTINGS_FILE


SETTING_KEY = 'check_locked_files'


def is_enabled():
	return get_setting(SETTINGS_FILE, SETTING_KEY, True)


def raise_if_locked(os_path):
	if PLATFORM != 'Windows' or not is_enabled():
		return
	try:
		_open_for_delete(os_path)
	except OSError as error:
		error_code = getattr(error, 'winerror', None) or error.errno
		if error_code in (32, 33):
			raise PermissionError(
				errno.EACCES,
				'The file is in use by another program',
				os_path
			) from error


def _open_for_delete(os_path):
	kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
	create_file = kernel32.CreateFileW
	create_file.argtypes = (
		wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
		wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
	)
	create_file.restype = wintypes.HANDLE
	close_handle = kernel32.CloseHandle
	close_handle.argtypes = (wintypes.HANDLE,)
	close_handle.restype = wintypes.BOOL
	share_read_write_delete = 0x1 | 0x2 | 0x4
	open_existing = 3
	file_attribute_normal = 0x80
	handle = create_file(
		os_path, 0x00010000, share_read_write_delete, None,
		open_existing, file_attribute_normal, None
	)
	if handle == wintypes.HANDLE(-1).value:
		error_code = ctypes.get_last_error()
		raise OSError(error_code, ctypes.FormatError(error_code), os_path)
	if not close_handle(handle):
		error_code = ctypes.get_last_error()
		raise OSError(error_code, ctypes.FormatError(error_code), os_path)
