"""Refresh visible folders when Windows reports shell status changes."""

import ctypes
from ctypes import wintypes
import ntpath
from PyQt5.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QWidget

from fman.impl.model.table import invalidate_icons
from fman.url import as_url


_CHANGE_MESSAGE = 0x8000 + 0x354
_BATCH_DELAY_MS = 300
_SHCNE_ALLEVENTS = 0x7FFFFFFF
_SHCNRF_SHELL_LEVEL = 0x0002
_SHCNRF_NEW_DELIVERY = 0x8000
_SHCNE_UPDATEDIR = 0x00001000


class ShellChangeBatch:
	"""Collect the parent folders of changed shell items until a flush."""

	def __init__(self):
		self._folders = set()

	def add(self, path, include_path=False):
		folder = ntpath.dirname(path)
		if folder:
			self._folders.add(as_url(folder))
		if include_path:
			self._folders.add(as_url(path))

	def flush(self):
		folders = tuple(sorted(self._folders))
		self._folders.clear()
		return folders


class ShellChangeListener(QObject):
	"""Debounce shell notices and reload only panes showing changed folders."""

	def __init__(self, window, overlays_enabled, notification_source=None):
		super().__init__()
		self._window = window
		self._overlays_enabled = overlays_enabled
		self._batch = ShellChangeBatch()
		self._timer = QTimer(self)
		self._timer.setSingleShot(True)
		self._timer.setInterval(_BATCH_DELAY_MS)
		self._timer.timeout.connect(self._flush)
		self._source = notification_source or \
			_ShellChangeNotificationSource(self._on_changed_paths)
		if notification_source is not None:
			self._source.set_callback(self._on_changed_paths)

	def _on_changed_paths(self, paths, event_id=0):
		if not self._overlays_enabled():
			return
		for path in paths:
			self._batch.add(path, include_path=event_id == _SHCNE_UPDATEDIR)
		if paths:
			self._timer.start()

	def _flush(self):
		folders = self._batch.flush()
		if not folders or not self._overlays_enabled():
			return
		changed_folders = {folder.casefold() for folder in folders}
		panes = [
			pane for pane in self._window.get_panes()
			if pane.get_location().casefold() in changed_folders
		]
		if panes:
			invalidate_icons()
			for pane in panes:
				pane.reload()

	def close(self):
		self._timer.stop()
		self._source.close()


class _ShellChangeNotificationSource(QAbstractNativeEventFilter):
	"""Receive SHChangeNotify messages on a private hidden Qt window."""

	def __init__(self, callback):
		super().__init__()
		self._callback = callback
		self._window = QWidget(None, Qt.Tool)
		self._window.setAttribute(Qt.WA_DontShowOnScreen)
		self._window.hide()
		self._hwnd = int(self._window.winId())
		self._app = QApplication.instance()
		self._app.installNativeEventFilter(self)
		self._shell32 = ctypes.WinDLL('shell32', use_last_error=True)
		self._register()

	def _register(self):
		class _SHChangeNotifyEntry(ctypes.Structure):
			_fields_ = [('pidl', ctypes.c_void_p), ('recursive', wintypes.BOOL)]

		self._shell32.SHChangeNotifyRegister.restype = wintypes.ULONG
		self._shell32.SHChangeNotifyRegister.argtypes = (
			wintypes.HWND, ctypes.c_int, wintypes.LONG, wintypes.UINT,
			ctypes.c_int, ctypes.POINTER(_SHChangeNotifyEntry)
		)
		entry = _SHChangeNotifyEntry(None, True)
		sources = _SHCNRF_SHELL_LEVEL | _SHCNRF_NEW_DELIVERY
		self._registration = self._shell32.SHChangeNotifyRegister(
			self._hwnd, sources, _SHCNE_ALLEVENTS, _CHANGE_MESSAGE, 1,
			ctypes.byref(entry)
		)
		if not self._registration:
			self._app.removeNativeEventFilter(self)
			self._window.close()
			raise ctypes.WinError(ctypes.get_last_error())

	def nativeEventFilter(self, event_type, message):
		if bytes(event_type) != b'windows_generic_MSG':
			return False, 0
		msg = _MSG.from_address(int(message))
		if msg.hwnd != self._hwnd or msg.message != _CHANGE_MESSAGE:
			return False, 0
		paths, event_id = _paths_from_notification(
			self._shell32, msg.wParam, msg.lParam
		)
		if paths:
			self._callback(paths, event_id)
		return False, 0

	def close(self):
		if self._registration:
			self._shell32.SHChangeNotifyDeregister(self._registration)
			self._registration = 0
		self._app.removeNativeEventFilter(self)
		self._window.close()


class _POINT(ctypes.Structure):
	_fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]


class _MSG(ctypes.Structure):
	_fields_ = [
		('hwnd', wintypes.HWND), ('message', wintypes.UINT),
		('wParam', wintypes.WPARAM), ('lParam', wintypes.LPARAM),
		('time', wintypes.DWORD), ('pt', _POINT)
	]


def _paths_from_notification(shell32, notification, event):
	"""Copy filesystem paths from a new-delivery shell notification."""
	items = (ctypes.c_void_p * 2)()
	event_id = wintypes.LONG()
	shell32.SHChangeNotification_Lock.restype = ctypes.c_void_p
	shell32.SHChangeNotification_Lock.argtypes = (
		wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
		ctypes.POINTER(wintypes.LONG)
	)
	locked = shell32.SHChangeNotification_Lock(
		notification, event, items, ctypes.byref(event_id)
	)
	if not locked:
		return (), 0
	try:
		shell32.SHGetPathFromIDListW.argtypes = (
			ctypes.c_void_p, wintypes.LPWSTR
		)
		shell32.SHGetPathFromIDListW.restype = wintypes.BOOL
		paths = []
		for pidl in items:
			if not pidl:
				continue
			path = ctypes.create_unicode_buffer(32768)
			if shell32.SHGetPathFromIDListW(pidl, path):
				paths.append(path.value)
		return tuple(paths), event_id.value
	finally:
		shell32.SHChangeNotification_Unlock.argtypes = (wintypes.HANDLE,)
		shell32.SHChangeNotification_Unlock(locked)

