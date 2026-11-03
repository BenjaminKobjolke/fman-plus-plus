"""Settings and Windows install checks for unattended updates."""
import os
import sys
import time

from fbs_runtime.application_context import is_frozen
from fman import PLATFORM
from fman.impl.portable import portable_app_dir

from core.settings import get_setting, SETTINGS_FILE

if sys.platform == 'win32':
	import winreg
else:
	winreg = None


AUTO_UPDATE_SETTING = 'auto_update'
AUTO_UPDATE_INTERVAL_SETTING = 'auto_update_interval_hours'
DEFAULT_INTERVAL_HOURS = 24
MIN_INTERVAL_HOURS = 1
MAX_INTERVAL_HOURS = 720
COUNTDOWN_SECONDS = 30
TIMER_SLACK_SECONDS = 10 * 60
UNSUPPORTED_MESSAGE = (
	'Automatic updates only work with the installed Windows version.'
)
REGISTRY_KEY = r'Software\fman'
UNINSTALLER_NAME = 'uninstall.exe'

_last_check_time = None


def is_enabled():
	"""Return whether the user enabled automatic updates."""
	return get_setting(SETTINGS_FILE, AUTO_UPDATE_SETTING, False) is True


def interval_hours():
	"""Return the configured interval when it is within the supported range."""
	value = get_setting(
		SETTINGS_FILE, AUTO_UPDATE_INTERVAL_SETTING, DEFAULT_INTERVAL_HOURS
	)
	if type(value) is not int or not MIN_INTERVAL_HOURS <= value <= MAX_INTERVAL_HOURS:
		return DEFAULT_INTERVAL_HOURS
	return value


def check_interval_seconds():
	"""Return the silent check interval, retaining daily checks when inactive."""
	if is_enabled() and is_supported():
		return interval_hours() * 60 * 60
	return DEFAULT_INTERVAL_HOURS * 60 * 60


def is_supported():
	"""Return whether this process can safely run the Windows installer."""
	if PLATFORM != 'Windows' or not is_frozen() or portable_app_dir() is not None:
		return False
	app_dir = os.path.dirname(sys.executable)
	if not os.path.isfile(os.path.join(app_dir, UNINSTALLER_NAME)):
		return False
	return get_install_mode() is not None


def get_install_mode():
	"""Return the NSIS install-mode switch matching this executable's folder."""
	if winreg is None:
		return None
	install_dir = os.path.normcase(os.path.normpath(os.path.dirname(sys.executable)))
	locations = (
		(winreg.HKEY_CURRENT_USER, winreg.KEY_READ, '/CurrentUser'),
		(
			winreg.HKEY_LOCAL_MACHINE,
			winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
			'/AllUsers'
		),
	)
	for hive, access, mode in locations:
		try:
			with winreg.OpenKey(hive, REGISTRY_KEY, 0, access) as key:
				registered_dir = winreg.QueryValueEx(key, None)[0]
		except OSError:
			continue
		if isinstance(registered_dir, str) and os.path.normcase(
			os.path.normpath(registered_dir)
		) == install_dir:
			return mode
	return None


def installer_command(setup_path):
	"""Build the NSIS silent command while keeping its required final /D value."""
	mode = get_install_mode()
	if mode is None:
		return None
	install_dir = os.path.dirname(sys.executable)
	# NSIS requires /D= as the last, unquoted argument; Popen(list) quotes it.
	return '"%s" /S %s /D=%s' % (setup_path, mode, install_dir)


def is_check_due(now=None):
	"""Return whether a timer tick may check, recording each due check in memory."""
	global _last_check_time
	if now is None:
		now = time.monotonic()
	if _last_check_time is None:
		_last_check_time = now
		return True
	if now - _last_check_time + TIMER_SLACK_SECONDS < check_interval_seconds():
		return False
	_last_check_time = now
	return True
