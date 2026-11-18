"""Read and control native Windows dialogs used by the installer."""

import ctypes
from ctypes import POINTER, Structure, byref, c_void_p
from ctypes import create_string_buffer, create_unicode_buffer
from ctypes.wintypes import BOOL, DWORD, HWND, LPARAM, LPCWSTR, LPVOID, UINT
from dataclasses import dataclass
import os
from pathlib import Path


GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
BM_CLICK = 0x00F5
WM_CLOSE = 0x0010
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
DIALOG_CLASS = '#32770'
BUTTON_CLASS = 'Button'
STATIC_CLASS = 'Static'


@dataclass(frozen=True)
class NativeButton:
	control_id: int
	label: str

	def to_dict(self):
		return {'id': self.control_id, 'label': self.label}


@dataclass(frozen=True)
class NativeWindow:
	hwnd: int
	pid: int
	title: str
	class_name: str

	def to_dict(self):
		return {'hwnd': self.hwnd, 'pid': self.pid,
			'title': self.title, 'class_name': self.class_name}


@dataclass(frozen=True)
class NativeDialog:
	hwnd: int
	pid: int
	title: str
	text: str
	buttons: tuple[NativeButton, ...]
	topmost: bool

	def to_dict(self):
		return {
			'hwnd': self.hwnd, 'pid': self.pid, 'title': self.title,
			'text': self.text, 'buttons': [button.to_dict() for button in self.buttons],
			'topmost': self.topmost,
		}


def _user32():
	if os.name != 'nt':
		raise OSError('Native Windows dialogs are available only on Windows.')
	user32 = ctypes.WinDLL('user32', use_last_error=True)
	callback = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
	user32.EnumWindows.argtypes = [callback, LPARAM]
	user32.EnumWindows.restype = BOOL
	user32.EnumChildWindows.argtypes = [HWND, callback, LPARAM]
	user32.EnumChildWindows.restype = BOOL
	user32.IsWindowVisible.argtypes = [HWND]
	user32.IsWindowVisible.restype = BOOL
	user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
	user32.GetWindowThreadProcessId.restype = DWORD
	user32.GetWindowTextLengthW.argtypes = [HWND]
	user32.GetWindowTextLengthW.restype = ctypes.c_int
	user32.GetWindowTextW.argtypes = [HWND, ctypes.c_wchar_p, ctypes.c_int]
	user32.GetWindowTextW.restype = ctypes.c_int
	user32.GetClassNameW.argtypes = [HWND, ctypes.c_wchar_p, ctypes.c_int]
	user32.GetClassNameW.restype = ctypes.c_int
	user32.GetDlgCtrlID.argtypes = [HWND]
	user32.GetDlgCtrlID.restype = ctypes.c_int
	user32.GetDlgItem.argtypes = [HWND, ctypes.c_int]
	user32.GetDlgItem.restype = HWND
	get_window_long = getattr(user32, 'GetWindowLongPtrW', user32.GetWindowLongW)
	get_window_long.argtypes = [HWND, ctypes.c_int]
	get_window_long.restype = ctypes.c_ssize_t
	user32.SendMessageW.argtypes = [HWND, UINT, ctypes.c_size_t, ctypes.c_ssize_t]
	user32.SendMessageW.restype = ctypes.c_ssize_t
	user32.PostMessageW.argtypes = [HWND, UINT, ctypes.c_size_t, ctypes.c_ssize_t]
	user32.PostMessageW.restype = BOOL
	return user32


def _text(user32, hwnd):
	length = user32.GetWindowTextLengthW(hwnd)
	buffer = create_unicode_buffer(length + 1)
	user32.GetWindowTextW(hwnd, buffer, len(buffer))
	return buffer.value


def _class_name(user32, hwnd):
	buffer = create_unicode_buffer(256)
	user32.GetClassNameW(hwnd, buffer, len(buffer))
	return buffer.value


def windows_for_pids(pids):
	user32 = _user32()
	wanted = {int(pid) for pid in pids}
	windows = []
	callback_type = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)

	@callback_type
	def visit(hwnd, _):
		if not user32.IsWindowVisible(hwnd):
			return True
		pid = DWORD()
		user32.GetWindowThreadProcessId(hwnd, byref(pid))
		if pid.value in wanted:
			windows.append(NativeWindow(
				int(hwnd), pid.value, _text(user32, hwnd), _class_name(user32, hwnd)))
		return True

	user32.EnumWindows(visit, 0)
	return windows


def window_titles(pid):
	return [window.title for window in windows_for_pids({pid})]


def read_dialog(hwnd, pid=None):
	user32 = _user32()
	if _class_name(user32, hwnd) != DIALOG_CLASS:
		return None
	children = []
	callback_type = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)

	@callback_type
	def visit(child, _):
		class_name = _class_name(user32, child)
		label = _text(user32, child).replace('&', '')
		if class_name == BUTTON_CLASS:
			children.append(NativeButton(user32.GetDlgCtrlID(child), label))
		elif class_name == STATIC_CLASS and label.strip():
			children.append(label.strip())
		return True

	user32.EnumChildWindows(hwnd, visit, 0)
	if pid is None:
		pid_value = DWORD()
		user32.GetWindowThreadProcessId(hwnd, byref(pid_value))
		pid = pid_value.value
	get_window_long = getattr(user32, 'GetWindowLongPtrW', user32.GetWindowLongW)
	style = get_window_long(hwnd, GWL_EXSTYLE)
	return NativeDialog(
		int(hwnd), int(pid), _text(user32, hwnd),
		'\n'.join(value for value in children if isinstance(value, str)),
		tuple(value for value in children if isinstance(value, NativeButton)),
		bool(style & WS_EX_TOPMOST),
	)


def dialogs_for_process(pid):
	return [dialog for window in windows_for_pids({pid})
		if (dialog := read_dialog(window.hwnd, pid)) is not None]


def click_dialog_button(dialog, control_id):
	user32 = _user32()
	button = next((button for button in dialog.buttons
		if button.control_id == control_id), None)
	if button is None:
		raise ValueError('Dialog has no button with id %s.' % control_id)
	# Find the child by its dialog control id, then send the button command.
	child = user32.GetDlgItem(dialog.hwnd, control_id)
	if not child:
		raise RuntimeError('Could not find dialog button %s.' % control_id)
	user32.SendMessageW(child, BM_CLICK, 0, 0)
	return button


def close_window(hwnd):
	_user32().PostMessageW(hwnd, WM_CLOSE, 0, 0)


class _FixedFileInfo(Structure):
	_fields_ = [
		('dwSignature', DWORD), ('dwStrucVersion', DWORD),
		('dwFileVersionMS', DWORD), ('dwFileVersionLS', DWORD),
		('dwProductVersionMS', DWORD), ('dwProductVersionLS', DWORD),
		('dwFileFlagsMask', DWORD), ('dwFileFlags', DWORD),
		('dwFileOS', DWORD), ('dwFileType', DWORD),
		('dwFileSubtype', DWORD), ('dwFileDateMS', DWORD),
		('dwFileDateLS', DWORD),
	]


def read_file_version(path):
	if os.name != 'nt':
		raise OSError('Windows file versions are available only on Windows.')
	version = ctypes.WinDLL('version', use_last_error=True)
	path = str(Path(path))
	ignored = DWORD()
	version.GetFileVersionInfoSizeW.argtypes = [LPCWSTR, ctypes.POINTER(DWORD)]
	version.GetFileVersionInfoSizeW.restype = DWORD
	version.GetFileVersionInfoW.argtypes = [LPCWSTR, DWORD, DWORD, LPVOID]
	version.GetFileVersionInfoW.restype = BOOL
	version.VerQueryValueW.argtypes = [
		LPVOID, LPCWSTR, ctypes.POINTER(c_void_p), ctypes.POINTER(UINT)]
	version.VerQueryValueW.restype = BOOL
	size = version.GetFileVersionInfoSizeW(path, byref(ignored))
	if not size:
		raise OSError('Could not read file version: %s' % path)
	data = create_string_buffer(size)
	if not version.GetFileVersionInfoW(path, 0, size, data):
		raise OSError('Could not read file version: %s' % path)
	value = c_void_p()
	length = UINT()
	if not version.VerQueryValueW(data, '\\', byref(value), byref(length)):
		raise OSError('Could not read file version: %s' % path)
	info = ctypes.cast(value, POINTER(_FixedFileInfo)).contents
	parts = (info.dwFileVersionMS >> 16, info.dwFileVersionMS & 0xFFFF,
		info.dwFileVersionLS >> 16, info.dwFileVersionLS & 0xFFFF)
	return '.'.join(str(part) for part in parts)
