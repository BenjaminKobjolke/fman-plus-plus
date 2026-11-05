"""Manage fman's optional per-user Windows Explorer replacement entries."""

import ctypes
import logging
import re
import sys
import winreg

from fman.impl import autostart


SETTING = 'explorer_replacement'
VERB = 'fman'
DIRECTORY_CLASS = r'Software\Classes\Directory'
DRIVE_CLASS = r'Software\Classes\Drive'
WIN_E_CLSID = '{52205fd8-5dfb-447d-801a-d0b52f2e83e1}'
THIS_PC_CLSID = '{20D04FE0-3AEA-1069-A2D8-08002B30309D}'
CLASSES_KEY = r'Software\Classes'
STATUS_ON = 'Folders, Win+E and This PC now open in fman'
STATUS_OFF = 'Folders, Win+E and This PC now open in Explorer'
STATUS_UNSUPPORTED = 'Explorer replacement works only in the installed fman'
STATUS_TAKEN_OVER = (
	'Another program now opens folders; Explorer replacement was turned off'
)

_LOG = logging.getLogger(__name__)
_CLSID_COMMANDS = (
	(WIN_E_CLSID, r'shell\opennewwindow\command', ''),
	(THIS_PC_CLSID, r'shell\open\command', ' drives://'),
)
_SHELL_CLASSES = (DIRECTORY_CLASS, DRIVE_CLASS)
_FMAN_COMMAND = re.compile(r'^".*\\fman\.exe"', re.IGNORECASE)


def _notify_association_change():
	try:
		ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
	except Exception:
		_LOG.exception('Could not notify Windows that file associations changed.')


def _command_path(suffix=''):
	return '"{}"{}'.format(sys.executable, suffix)


def _set_value(path, name, value):
	with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
		winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _read_value(path, name=''):
	try:
		with winreg.OpenKey(
			winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ
		) as key:
			return winreg.QueryValueEx(key, name)[0]
	except FileNotFoundError:
		return None


def _delete_tree(root, path):
	try:
		with winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
			while True:
				try:
					child = winreg.EnumKey(key, 0)
				except OSError:
					break
				_delete_tree(key, child)
		winreg.DeleteKey(root, path)
	except FileNotFoundError:
		pass


def _clsid_path(clsid, suffix):
	return CLASSES_KEY + '\\CLSID\\' + clsid + '\\' + suffix


def _is_fman_command(command):
	return isinstance(command, str) and _FMAN_COMMAND.match(command) is not None


def enable():
	"""Create or refresh fman's folder, drive, Win+E and This PC handlers."""
	for class_path in _SHELL_CLASSES:
		shell_path = class_path + r'\shell'
		_set_value(shell_path, '', VERB)
		_set_value(shell_path + '\\' + VERB, '', 'Open in fman')
		_set_value(
			shell_path + '\\' + VERB + r'\command', '', _command_path(' "%1"')
		)
	for clsid, suffix, command_suffix in _CLSID_COMMANDS:
		command_path = _clsid_path(clsid, suffix)
		_set_value(command_path, '', _command_path(command_suffix))
		_set_value(command_path, 'DelegateExecute', '')
	_notify_association_change()


def disable():
	"""Remove fman's handlers while preserving handlers another app installed."""
	for class_path in _SHELL_CLASSES:
		shell_path = class_path + r'\shell'
		_delete_tree(winreg.HKEY_CURRENT_USER, shell_path + '\\' + VERB)
		if _read_value(shell_path) == VERB:
			try:
				with winreg.OpenKey(
					winreg.HKEY_CURRENT_USER, shell_path, 0, winreg.KEY_SET_VALUE
				) as key:
					winreg.DeleteValue(key, '')
			except FileNotFoundError:
				pass
	for clsid, suffix, unused in _CLSID_COMMANDS:
		command_path = _clsid_path(clsid, suffix)
		if _is_fman_command(_read_value(command_path)):
			_delete_tree(
				winreg.HKEY_CURRENT_USER,
				CLASSES_KEY + '\\CLSID\\' + clsid,
			)
	_notify_association_change()


def is_owned():
	"""Return whether all four Windows handlers still point to fman."""
	if any(_read_value(path + r'\shell') != VERB for path in _SHELL_CLASSES):
		return False
	return all(
		_is_fman_command(_read_value(_clsid_path(clsid, suffix)))
		for clsid, suffix, unused in _CLSID_COMMANDS
	)


def apply(settings):
	"""Refresh an enabled redirect or turn it off after another app takes over."""
	if not autostart.is_supported() or not settings.get(SETTING, False):
		return None
	if is_owned():
		try:
			enable()
		except OSError:
			_LOG.exception('Could not refresh Explorer replacement registry entries.')
		return None
	disable()
	settings.pop(SETTING, None)
	settings.flush()
	return STATUS_TAKEN_OVER


def toggle(settings):
	"""Toggle Explorer replacement, persisting only after registry changes work."""
	if not autostart.is_supported():
		return STATUS_UNSUPPORTED
	enabled = not settings.get(SETTING, False)
	try:
		if enabled:
			enable()
		else:
			disable()
	except OSError as error:
		_LOG.exception('Could not change Explorer replacement setting.')
		return 'Could not change Explorer replacement: {}'.format(error)
	if enabled:
		settings[SETTING] = True
		status = STATUS_ON
	else:
		settings.pop(SETTING, None)
		status = STATUS_OFF
	settings.flush()
	return status


def fix_shell_arg(arg):
	"""Repair Windows' escaped trailing quote for quoted drive-root arguments."""
	if re.fullmatch(r'[A-Za-z]:"', arg):
		return arg[:2] + '\\'
	return arg
