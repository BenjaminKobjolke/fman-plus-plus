"""Control whether Windows groups fman windows into one taskbar button."""

import ctypes
import logging
import os
from collections.abc import Mapping

from fman import APP_NAME


SETTING = 'taskbar_grouping'
_LOG = logging.getLogger(__name__)
_set_app_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
_set_app_id.argtypes = [ctypes.c_wchar_p]
_set_app_id.restype = ctypes.c_long


def app_id() -> str:
	"""Return the taskbar identity unique to this fman process."""
	return APP_NAME + '.' + str(os.getpid())


def apply(settings: Mapping[str, object]) -> None:
	"""Assign a private taskbar identity when grouping is disabled."""
	if settings.get(SETTING, True):
		return
	try:
		hresult = _set_app_id(app_id())
	except OSError:
		_LOG.exception('Could not set the Windows taskbar application ID.')
		return
	if hresult:
		_LOG.warning(
			'Could not set the Windows taskbar application ID (HRESULT 0x%08X).',
			hresult,
		)
