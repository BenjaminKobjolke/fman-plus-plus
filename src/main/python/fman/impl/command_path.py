"""Manage fman's optional Windows command-line PATH entry."""

import ctypes
import logging
import os
import sys

try:
	import winreg
except ImportError:  # Not available on platforms where this command is unsupported.
	winreg = None

from fman.impl.portable import portable_app_dir


ENVIRONMENT_KEY = 'Environment'
PATH_VALUE = 'Path'
APP_KEY = r'Software\fman'
OPT_OUT_VALUE = 'NoPathEntry'  # Installer.nsi reads the same value name.
STATUS_ON = 'fman command added to PATH. Open a new terminal to use it.'
STATUS_ON_PORTABLE = STATUS_ON + ' Switch it off before you move this folder.'
STATUS_OFF = 'fman command removed from PATH.'
STATUS_UNSUPPORTED = 'The fman command in PATH is only available on Windows.'

_LOG = logging.getLogger(__name__)


def is_supported():
	"""Return whether this is a frozen Windows build."""
	return sys.platform == 'win32' and getattr(sys, 'frozen', False)


def bin_dir():
	"""Return the directory containing fman's command-line shim."""
	return os.path.join(os.path.dirname(sys.executable), 'bin')


def _same_dir(a, b):
	return os.path.normcase(a.rstrip('\\/')) == os.path.normcase(b.rstrip('\\/'))


def contains(path_value, entry):
	return any(_same_dir(part, entry) for part in path_value.split(';') if part)


def with_entry(path_value, entry):
	parts = [part for part in path_value.split(';') if part]
	if not any(_same_dir(part, entry) for part in parts):
		parts.append(entry)
	return ';'.join(parts)


def without_entry(path_value, entry):
	return ';'.join(
		part for part in path_value.split(';') if part and not _same_dir(part, entry)
	)


def _read_user_path():
	try:
		with winreg.OpenKey(
			winreg.HKEY_CURRENT_USER, ENVIRONMENT_KEY, 0, winreg.KEY_QUERY_VALUE
		) as key:
			return winreg.QueryValueEx(key, PATH_VALUE)
	except FileNotFoundError:
		return '', winreg.REG_EXPAND_SZ


def _write_user_path(value, value_type):
	with winreg.OpenKey(
		winreg.HKEY_CURRENT_USER, ENVIRONMENT_KEY, 0, winreg.KEY_SET_VALUE
	) as key:
		winreg.SetValueEx(key, PATH_VALUE, 0, value_type, value)


def _set_opt_out(enabled):
	with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APP_KEY) as key:
		if enabled:
			winreg.SetValueEx(key, OPT_OUT_VALUE, 0, winreg.REG_DWORD, 1)
		else:
			try:
				winreg.DeleteValue(key, OPT_OUT_VALUE)
			except FileNotFoundError:
				pass


def _broadcast_environment_change():
	ctypes.windll.user32.SendMessageTimeoutW(
		0xFFFF, 0x001A, 0, 'Environment', 0x0002, 5000, None
	)


def toggle():
	"""Toggle the current fman executable's bin directory in the user PATH."""
	if not is_supported():
		return STATUS_UNSUPPORTED

	entry = bin_dir()
	try:
		path_value, value_type = _read_user_path()
		adding = not contains(path_value, entry)
		updated = (
			with_entry(path_value, entry)
			if adding else without_entry(path_value, entry)
		)
		_write_user_path(updated, value_type)
		portable = portable_app_dir() is not None
		if not portable:
			_set_opt_out(not adding)
		_broadcast_environment_change()
	except OSError as error:
		_LOG.exception('Could not change the fman command in PATH.')
		return 'Could not change the fman command in PATH: {}'.format(error)

	if adding:
		return STATUS_ON_PORTABLE if portable else STATUS_ON
	return STATUS_OFF
