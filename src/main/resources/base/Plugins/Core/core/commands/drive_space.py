"""Refresh drive capacity while the drives list is visible.

Other programs can change free space without fman navigating. The timer is
active only on drives:// so it adds no periodic filesystem work elsewhere.
"""
from core.settings import get_setting
from fman import DirectoryPaneListener
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtCore import QTimer

__all__ = ['RefreshDriveSpace']

_SETTING_KEY = 'drive_space_refresh_seconds'
_DEFAULT_SECONDS = 10
_DRIVES_URL = 'drives://'


def _get_refresh_seconds():
	seconds = get_setting('Core Settings.json', _SETTING_KEY, _DEFAULT_SECONDS)
	if type(seconds) is not int or seconds < 0:
		return _DEFAULT_SECONDS
	return seconds


def _should_refresh(url, seconds):
	return url == _DRIVES_URL and seconds > 0


class RefreshDriveSpace(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._timer = None

	def on_path_changed(self):
		_update_refresh_timer(self)


@run_in_main_thread
def _update_refresh_timer(listener):
	seconds = _get_refresh_seconds()
	if listener._timer is None:
		listener._timer = QTimer(listener.pane._widget)
		listener._timer.timeout.connect(listener.pane.reload)
	if _should_refresh(listener.pane.get_path(), seconds):
		listener._timer.start(seconds * 1000)
	else:
		listener._timer.stop()
