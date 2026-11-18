"""Read real file thumbnails from the Windows shell."""

import ctypes
from ctypes import wintypes
from fman import PLATFORM
from threading import local
from uuid import UUID

_IID_SHELL_ITEM_IMAGE_FACTORY = UUID(
	'BCC18B79-BA16-442F-80C4-8A59C30C463B'
)
_SIIGBF_THUMBNAILONLY = 0x00000008
_COM = local()


class _GUID(ctypes.Structure):
	_fields_ = [
		('Data1', wintypes.DWORD),
		('Data2', wintypes.WORD),
		('Data3', wintypes.WORD),
		('Data4', ctypes.c_ubyte * 8),
	]

	@classmethod
	def from_uuid(cls, value: UUID):
		data = value.bytes_le
		return cls(
			int.from_bytes(data[:4], 'little'),
			int.from_bytes(data[4:6], 'little'),
			int.from_bytes(data[6:8], 'little'),
			(ctypes.c_ubyte * 8).from_buffer_copy(data[8:]),
		)


class _SIZE(ctypes.Structure):
	_fields_ = [('cx', wintypes.LONG), ('cy', wintypes.LONG)]


def shell_thumbnail(path: str, size: int):
	"""Return a Windows shell thumbnail image, or `None` when unavailable."""
	if PLATFORM != 'Windows':
		return None
	item = ctypes.c_void_p()
	bitmap = ctypes.c_void_p()
	vtable = None
	try:
		_initialize_com_for_thread()
		shell32 = ctypes.WinDLL('shell32', use_last_error=True)
		shell32.SHCreateItemFromParsingName.restype = ctypes.c_long
		shell32.SHCreateItemFromParsingName.argtypes = (
			wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(_GUID),
			ctypes.POINTER(ctypes.c_void_p),
		)
		iid = _GUID.from_uuid(_IID_SHELL_ITEM_IMAGE_FACTORY)
		result = shell32.SHCreateItemFromParsingName(
			path, None, ctypes.byref(iid), ctypes.byref(item)
		)
		if result < 0 or not item.value:
			return None
		vtable = ctypes.cast(
			item, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
		).contents
		get_image = ctypes.WINFUNCTYPE(
			ctypes.c_long, ctypes.c_void_p, _SIZE, wintypes.DWORD,
			ctypes.POINTER(ctypes.c_void_p),
		)(vtable[3])
		result = get_image(
			item, _SIZE(size, size), _SIIGBF_THUMBNAILONLY,
			ctypes.byref(bitmap),
		)
		if result < 0 or not bitmap.value:
			return None
		from PyQt5.QtWinExtras import QtWin
		image = QtWin.fromHBITMAP(bitmap.value).toImage().copy()
		return None if image.isNull() else image
	except Exception:
		return None
	finally:
		if bitmap.value:
			ctypes.WinDLL('gdi32', use_last_error=True).DeleteObject(bitmap)
		if item.value and vtable is None:
			vtable = ctypes.cast(
				item, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
			).contents
		if item.value:
			release = ctypes.WINFUNCTYPE(
				ctypes.c_ulong, ctypes.c_void_p
			)(vtable[2])
			release(item)


def _initialize_com_for_thread():
	if not getattr(_COM, 'initialized', False):
		import pythoncom
		pythoncom.CoInitialize()
		_COM.initialized = True
