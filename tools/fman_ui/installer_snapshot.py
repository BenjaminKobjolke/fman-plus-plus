"""Snapshot per-user installer side effects and restore them afterward."""

from base64 import b64decode, b64encode
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Protocol


ENVIRONMENT_KEY = r'Environment'
FMAN_KEY = r'Software\fman'
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\fman'
PATH_VALUE = 'Path'


class UserRegistry(Protocol):
	def read_value(self, key, name): ...
	def write_value(self, key, name, value, value_type): ...
	def delete_value(self, key, name): ...
	def key_exists(self, key): ...
	def delete_key(self, key): ...


class WindowsUserRegistry:
	"""HKCU adapter that preserves registry value types."""

	def __init__(self):
		if os.name != 'nt':
			raise OSError('The installer session is available only on Windows.')
		import winreg
		self.winreg = winreg

	def read_value(self, key, name):
		try:
			with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, key) as handle:
				value, value_type = self.winreg.QueryValueEx(handle, name)
				return value, value_type
		except FileNotFoundError:
			return None

	def write_value(self, key, name, value, value_type):
		with self.winreg.CreateKeyEx(self.winreg.HKEY_CURRENT_USER, key, 0,
				self.winreg.KEY_SET_VALUE) as handle:
			self.winreg.SetValueEx(handle, name, 0, value_type, value)

	def delete_value(self, key, name):
		try:
			with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, key, 0,
					self.winreg.KEY_SET_VALUE) as handle:
				self.winreg.DeleteValue(handle, name)
		except FileNotFoundError:
			pass

	def key_exists(self, key):
		try:
			with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, key):
				return True
		except FileNotFoundError:
			return False

	def delete_key(self, key):
		try:
			with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, key) as handle:
				while True:
					try:
						child = self.winreg.EnumKey(handle, 0)
					except OSError:
						break
					self.delete_key(key + '\\' + child)
			self.winreg.DeleteKey(self.winreg.HKEY_CURRENT_USER, key)
		except FileNotFoundError:
			pass


def shortcut_paths():
	appdata = Path(os.environ.get('APPDATA', ''))
	programs = appdata / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
	return (programs / 'fman++.lnk', programs / 'fman.lnk')


@dataclass(frozen=True)
class ShortcutSnapshot:
	path: str
	existed: bool
	content: str | None

	def to_dict(self):
		return {'path': self.path, 'existed': self.existed, 'content': self.content}

	@classmethod
	def from_dict(cls, value):
		return cls(value['path'], value['existed'], value.get('content'))


@dataclass(frozen=True)
class UserInstallSnapshot:
	path_value: object
	path_type: int | None
	shortcuts: tuple[ShortcutSnapshot, ...]
	fman_key_existed: bool
	uninstall_key_existed: bool

	def to_dict(self):
		return {
			'path_value': self.path_value, 'path_type': self.path_type,
			'shortcuts': [shortcut.to_dict() for shortcut in self.shortcuts],
			'fman_key_existed': self.fman_key_existed,
			'uninstall_key_existed': self.uninstall_key_existed,
		}

	@classmethod
	def from_dict(cls, value):
		return cls(value.get('path_value'), value.get('path_type'),
			tuple(ShortcutSnapshot.from_dict(item) for item in value['shortcuts']),
			value['fman_key_existed'], value['uninstall_key_existed'])


def _snapshot_shortcut(path):
	path = Path(path)
	if not path.is_file():
		return ShortcutSnapshot(str(path), False, None)
	return ShortcutSnapshot(str(path), True,
		b64encode(path.read_bytes()).decode('ascii'))


def take_snapshot(user_registry=None):
	user_registry = user_registry or WindowsUserRegistry()
	path = user_registry.read_value(ENVIRONMENT_KEY, PATH_VALUE)
	return UserInstallSnapshot(
		None if path is None else path[0],
		None if path is None else path[1],
		tuple(_snapshot_shortcut(item) for item in shortcut_paths()),
		user_registry.key_exists(FMAN_KEY),
		user_registry.key_exists(UNINSTALL_KEY),
	)


def _restore_shortcut(shortcut):
	path = Path(shortcut.path)
	if shortcut.existed:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_bytes(b64decode(shortcut.content or ''))
	else:
		path.unlink(missing_ok=True)


def _broadcast_environment_change():
	if os.name != 'nt':
		return
	import ctypes
	result = ctypes.c_ulong()
	ctypes.windll.user32.SendMessageTimeoutW(
		0xFFFF, 0x001A, 0, 'Environment', 0x0002, 5000,
		ctypes.byref(result))


def restore_snapshot(snapshot, user_registry=None):
	user_registry = user_registry or WindowsUserRegistry()
	if snapshot.path_type is None:
		user_registry.delete_value(ENVIRONMENT_KEY, PATH_VALUE)
	else:
		user_registry.write_value(ENVIRONMENT_KEY, PATH_VALUE,
			snapshot.path_value, snapshot.path_type)
	_broadcast_environment_change()
	for shortcut in snapshot.shortcuts:
		_restore_shortcut(shortcut)
	if not snapshot.fman_key_existed:
		user_registry.delete_key(FMAN_KEY)
	if not snapshot.uninstall_key_existed:
		user_registry.delete_key(UNINSTALL_KEY)
	return {'path_restored': True, 'shortcuts_restored': len(snapshot.shortcuts)}
