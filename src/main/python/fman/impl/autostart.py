"""Manage fman's optional Windows sign-in startup entry."""

import logging
import sys
import winreg

from fman.impl.portable import portable_app_dir


SETTING = 'start_with_windows'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_VALUE = 'fman'
TRAY_ARG = '--tray'
STATUS_ON = 'fman will start with Windows'
STATUS_OFF = 'fman will not start with Windows'
STATUS_UNSUPPORTED = 'Start with Windows works only in the installed fman'

_LOG = logging.getLogger(__name__)


def run_command():
	"""Return the quoted executable command that starts fman hidden in the tray."""
	return '"{}" {}'.format(sys.executable, TRAY_ARG)


def is_supported():
	"""Return whether this is an installed, frozen Windows build."""
	return (
		sys.platform == 'win32'
		and getattr(sys, 'frozen', False)
		and portable_app_dir() is None
	)


def enable():
	"""Create or refresh fman's per-user sign-in startup entry."""
	with winreg.OpenKey(
		winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
	) as key:
		winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, run_command())


def disable():
	"""Remove fman's per-user sign-in startup entry if it exists."""
	with winreg.OpenKey(
		winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
	) as key:
		try:
			winreg.DeleteValue(key, RUN_VALUE)
		except FileNotFoundError:
			pass


def apply(settings):
	"""Refresh the Run entry when sign-in startup is enabled."""
	if not is_supported() or not settings.get(SETTING, False):
		return
	try:
		enable()
	except OSError:
		_LOG.exception('Could not refresh Windows sign-in startup entry.')


def toggle(settings):
	"""Toggle sign-in startup, persisting only after registry changes succeed."""
	if not is_supported():
		return STATUS_UNSUPPORTED

	enabled = not settings.get(SETTING, False)
	try:
		if enabled:
			enable()
		else:
			disable()
	except OSError as error:
		_LOG.exception('Could not change Windows sign-in startup setting.')
		return 'Could not change start with Windows: {}'.format(error)

	if enabled:
		settings[SETTING] = True
		status = STATUS_ON
	else:
		settings.pop(SETTING)
		status = STATUS_OFF
	settings.flush()
	return status
