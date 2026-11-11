"""Read and write WSL links whose Linux-only targets Windows cannot follow."""

import ctypes
import os
from ctypes import wintypes


IO_REPARSE_TAG_LX_SYMLINK = 0xA000001D
ERROR_CANT_ACCESS_FILE = 1920
FSCTL_GET_REPARSE_POINT = 0x900A8
FSCTL_SET_REPARSE_POINT = 0x900A4
MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16 * 1024


def is_wsl_link(os_path: str) -> bool:
	return getattr(os.lstat(os_path), 'st_reparse_tag', 0) == IO_REPARSE_TAG_LX_SYMLINK


def read_reparse_data(os_path: str) -> bytes:
	kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
	create_file, device_io_control, close_handle = _configure_kernel32(kernel32)
	handle = _open_reparse_point(create_file, os_path, 0x80000000)
	try:
		buffer = ctypes.create_string_buffer(MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
		bytes_returned = wintypes.DWORD()
		if not device_io_control(
			handle, FSCTL_GET_REPARSE_POINT, None, 0, buffer, len(buffer),
			ctypes.byref(bytes_returned), None
		):
			_raise_last_error(os_path)
		return buffer.raw[:bytes_returned.value]
	finally:
		_close_handle(close_handle, handle, os_path)


def write_reparse_data(os_path: str, data: bytes) -> None:
	kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
	create_file, device_io_control, close_handle = _configure_kernel32(kernel32)
	handle = _open_reparse_point(create_file, os_path, 0x40000000)
	try:
		buffer = ctypes.create_string_buffer(data)
		if not device_io_control(
			handle, FSCTL_SET_REPARSE_POINT, buffer, len(data), None, 0,
			None, None
		):
			_raise_last_error(os_path)
	finally:
		_close_handle(close_handle, handle, os_path)


def _configure_kernel32(kernel32):
	create_file = kernel32.CreateFileW
	create_file.argtypes = (
		wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
		wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
	)
	create_file.restype = wintypes.HANDLE
	device_io_control = kernel32.DeviceIoControl
	device_io_control.argtypes = (
		wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
		wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
		wintypes.LPVOID
	)
	device_io_control.restype = wintypes.BOOL
	close_handle = kernel32.CloseHandle
	close_handle.argtypes = (wintypes.HANDLE,)
	close_handle.restype = wintypes.BOOL
	return create_file, device_io_control, close_handle


def _open_reparse_point(create_file, os_path: str, access: int):
	path = os.fspath(os_path)
	share_read_write_delete = 0x1 | 0x2 | 0x4
	open_existing = 3
	open_reparse_point = 0x00200000
	backup_semantics = 0x02000000
	handle = create_file(
		path, access, share_read_write_delete, None, open_existing,
		open_reparse_point | backup_semantics, None
	)
	if handle == wintypes.HANDLE(-1).value:
		_raise_last_error(path)
	return handle


def _close_handle(close_handle, handle, os_path: str) -> None:
	if not close_handle(handle):
		_raise_last_error(os_path)


def _raise_last_error(os_path: str) -> None:
	error_code = ctypes.get_last_error()
	raise OSError(error_code, ctypes.FormatError(error_code), os_path)
