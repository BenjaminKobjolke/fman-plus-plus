"""Read Windows shell overlay icons for custom fman icon sets."""

import ctypes
from ctypes import wintypes
from threading import Lock, local
from uuid import UUID

_SHGFI_SYSICONINDEX = 0x000004000
_SHGFI_OVERLAYINDEX = 0x000000040
_SHGFI_SMALLICON = 0x000000001
_ILD_TRANSPARENT = 0x000000001
_IID_IIMAGE_LIST = UUID('46eb5926-582e-4017-9fdf-e8998daa0950')
_IIMAGE_LIST_GET_OVERLAY_IMAGE = 31


class _GUID(ctypes.Structure):
	_fields_ = [
		('Data1', wintypes.DWORD),
		('Data2', wintypes.WORD),
		('Data3', wintypes.WORD),
		('Data4', ctypes.c_ubyte * 8),
	]

	@classmethod
	def from_uuid(cls, value):
		data = value.bytes_le
		return cls(
			int.from_bytes(data[:4], 'little'),
			int.from_bytes(data[4:6], 'little'),
			int.from_bytes(data[6:8], 'little'),
			(ctypes.c_ubyte * 8).from_buffer_copy(data[8:]),
		)


class _SHFILEINFO(ctypes.Structure):
	_fields_ = [
		('hIcon', wintypes.HICON),
		('iIcon', ctypes.c_int),
		('dwAttributes', wintypes.DWORD),
		('szDisplayName', wintypes.WCHAR * 260),
		('szTypeName', wintypes.WCHAR * 80),
	]


class ShellOverlays:
	"""Look up the shell overlay index and cache its small image by index."""

	def __init__(self):
		self._shell32 = ctypes.WinDLL('shell32', use_last_error=True)
		self._comctl32 = ctypes.WinDLL('comctl32', use_last_error=True)
		self._user32 = ctypes.WinDLL('user32', use_last_error=True)
		self._com = local()
		self._cache = {}
		self._image_list = None
		self._lock = Lock()

		self._shell32.SHGetFileInfoW.restype = ctypes.c_void_p
		self._shell32.SHGetFileInfoW.argtypes = (
			wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(_SHFILEINFO),
			wintypes.UINT, wintypes.UINT
		)
		self._comctl32.HIMAGELIST_QueryInterface.restype = ctypes.c_long
		self._comctl32.HIMAGELIST_QueryInterface.argtypes = (
			ctypes.c_void_p, ctypes.POINTER(_GUID),
			ctypes.POINTER(ctypes.c_void_p)
		)
		self._comctl32.ImageList_GetIcon.restype = wintypes.HICON
		self._comctl32.ImageList_GetIcon.argtypes = (
			ctypes.c_void_p, ctypes.c_int, wintypes.UINT
		)
		self._user32.DestroyIcon.argtypes = (wintypes.HICON,)
		self._user32.DestroyIcon.restype = wintypes.BOOL

	def overlay_index(self, path):
		"""Return the shell's one-based overlay slot for `path`, if any."""
		self._initialize_com_for_thread()
		info = _SHFILEINFO()
		flags = _SHGFI_SYSICONINDEX | _SHGFI_OVERLAYINDEX | _SHGFI_SMALLICON
		image_list = self._shell32.SHGetFileInfoW(
			path, 0, ctypes.byref(info), ctypes.sizeof(info), flags
		)
		if not image_list:
			return None
		self._image_list = image_list
		return _decode_overlay_index(info.iIcon)

	def pixmap(self, overlay_index):
		"""Return a cached Qt pixmap for a one-based shell overlay slot."""
		if not overlay_index:
			return None
		with self._lock:
			if overlay_index not in self._cache:
				self._cache[overlay_index] = self._load_pixmap(overlay_index)
			return self._cache[overlay_index]

	def _load_pixmap(self, overlay_index):
		self._initialize_com_for_thread()
		if not self._image_list:
			return None
		image_index = self._get_overlay_image_index(overlay_index)
		if image_index is None:
			return None
		hicon = self._comctl32.ImageList_GetIcon(
			self._image_list, image_index, _ILD_TRANSPARENT
		)
		if not hicon:
			return None
		try:
			from PyQt5.QtWinExtras import QtWin
			return QtWin.fromHICON(hicon)
		finally:
			self._user32.DestroyIcon(hicon)

	def _get_overlay_image_index(self, overlay_index):
		interface = ctypes.c_void_p()
		iid = _GUID.from_uuid(_IID_IIMAGE_LIST)
		result = self._comctl32.HIMAGELIST_QueryInterface(
			self._image_list, ctypes.byref(iid), ctypes.byref(interface)
		)
		if result < 0 or not interface.value:
			return None
		try:
			vtable = ctypes.cast(
				interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
			).contents
			get_overlay_image = ctypes.WINFUNCTYPE(
				ctypes.c_long, ctypes.c_void_p, ctypes.c_int,
				ctypes.POINTER(ctypes.c_int)
			)(vtable[_IIMAGE_LIST_GET_OVERLAY_IMAGE])
			image_index = ctypes.c_int()
			result = get_overlay_image(
				interface, overlay_index, ctypes.byref(image_index)
			)
			return image_index.value if result >= 0 else None
		finally:
			release = ctypes.WINFUNCTYPE(
				ctypes.c_ulong, ctypes.c_void_p
			)(vtable[2])
			release(interface)

	def _initialize_com_for_thread(self):
		if not getattr(self._com, 'initialized', False):
			import pythoncom
			# CoInitialize tolerates a thread that was already initialized in a
			# different apartment, unlike CoInitializeEx.
			pythoncom.CoInitialize()
			self._com.initialized = True


def _decode_overlay_index(icon_index):
	return (icon_index >> 24) & 0xff or None
