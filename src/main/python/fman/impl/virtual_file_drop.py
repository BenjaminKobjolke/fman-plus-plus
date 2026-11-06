"""Proxy Qt's native drop target so virtual files remain available to fman."""

import ctypes
import logging

import pythoncom
from win32com.server.util import wrap


# Qt requests FileContents only at lindex -1, so retain the native object.
_current_data_object = None
_inner_target = None
_proxy = None
_registered_target = None


def current_data_object() -> object | None:
	return _current_data_object


class _DropTargetProxy:
	_com_interfaces_ = [pythoncom.IID_IDropTarget]
	_public_methods_ = ['DragEnter', 'DragOver', 'DragLeave', 'Drop']

	def __init__(self, inner_target):
		self._inner_target = inner_target

	def DragEnter(self, data_object, key_state, point, effect):
		global _current_data_object
		_current_data_object = data_object
		try:
			return self._inner_target.DragEnter(
				data_object, key_state, point, effect)
		except BaseException:
			_current_data_object = None
			raise

	def DragOver(self, key_state, point, effect):
		return self._inner_target.DragOver(key_state, point, effect)

	def DragLeave(self):
		global _current_data_object
		try:
			return self._inner_target.DragLeave()
		finally:
			_current_data_object = None

	def Drop(self, data_object, key_state, point, effect):
		global _current_data_object
		_current_data_object = data_object
		try:
			return self._inner_target.Drop(
				data_object, key_state, point, effect)
		finally:
			_current_data_object = None


def install_drop_hook(hwnd: int) -> bool:
	global _inner_target, _proxy, _registered_target
	inner_target = None
	revoked = False
	try:
		get_prop = ctypes.windll.user32.GetPropW
		get_prop.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
		get_prop.restype = ctypes.c_void_p
		address = get_prop(hwnd, 'OleDropTargetInterface')
		if not address:
			logging.warning('Could not find Qt native drop target for fman window')
			return False
		inner_target = pythoncom.ObjectFromAddress(
			address, pythoncom.IID_IDropTarget)
		pythoncom.RevokeDragDrop(hwnd)
		revoked = True
		proxy = _DropTargetProxy(inner_target)
		registered_target = wrap(proxy, pythoncom.IID_IDropTarget)
		pythoncom.RegisterDragDrop(hwnd, registered_target)
	except Exception as error:
		if revoked:
			try:
				pythoncom.RegisterDragDrop(hwnd, inner_target)
			except Exception:
				logging.exception('Could not restore Qt native drop target')
		logging.warning('Could not install virtual file drop hook: %s', error)
		return False
	_inner_target, _proxy, _registered_target = (
		inner_target, proxy, registered_target)
	return True
