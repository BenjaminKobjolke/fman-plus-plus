"""Refresh folders by polling while fman is active.

Filesystem watchers lock Windows drives.
"""
from collections import namedtuple
from core.settings import get_setting, save_setting, SETTINGS_FILE
from fman import (
	ApplicationCommand, DirectoryPaneListener, PLATFORM, show_status_message
)
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from weakref import WeakSet


__all__ = [
	'RefreshFolders', 'ToggleLocalFolderRefresh', 'ToggleNetworkFolderRefresh',
	'ToggleFtpFolderRefresh'
]

_Category = namedtuple(
	'_Category', ('name', 'enabled_key', 'seconds_key', 'label')
)
LOCAL = _Category(
	'local', 'refresh_local_folders', 'local_folder_refresh_seconds', 'Local'
)
NETWORK = _Category(
	'network', 'refresh_network_folders', 'network_folder_refresh_seconds', 'Network'
)
FTP = _Category(
	'ftp', 'refresh_ftp_folders', 'ftp_folder_refresh_seconds', 'FTP'
)
_DEFAULT_SECONDS = 5
_FTP_SCHEMES = ('ftp://', 'ftps://', 'sftp://')
_listeners = WeakSet()


def _category_of(url):
	if url.startswith(_FTP_SCHEMES):
		return FTP
	if url.startswith('network://'):
		return NETWORK
	if not url.startswith('file://'):
		return None
	path = url[len('file://'):]
	if PLATFORM == 'Windows':
		if path.startswith('//'):
			return NETWORK
		if len(path) >= 4 and path[0] == '/' and path[2] == ':':
			drive = path[1:3]
		elif len(path) >= 3 and path[1] == ':':
			drive = path[:2]
		else:
			drive = None
		if drive is not None and _is_remote(drive + '\\'):
			return NETWORK
	return LOCAL


def _is_remote(path):
	from core.fs.local.windows.drives import _is_remote as is_remote
	return is_remote(path)


def _is_enabled(category):
	return get_setting(SETTINGS_FILE, category.enabled_key, False) is True


def _get_refresh_seconds(category):
	seconds = get_setting(SETTINGS_FILE, category.seconds_key, _DEFAULT_SECONDS)
	if type(seconds) is not int or seconds < 1:
		return _DEFAULT_SECONDS
	return seconds


class RefreshFolders(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._timer = None
		self._category = None
		_listeners.add(self)

	def on_path_changed(self):
		self._category = _category_of(self.pane.get_path())
		_update_refresh_timer(self)

	def _on_tick(self):
		app = QApplication.instance()
		if app is not None and app.applicationState() == Qt.ApplicationActive:
			self.pane._widget.reload_unless_pending()


@run_in_main_thread
def _update_refresh_timer(listener):
	if listener._timer is None:
		listener._timer = QTimer(listener.pane._widget)
		listener._timer.timeout.connect(listener._on_tick)
	category = listener._category
	if category is not None and _is_enabled(category):
		listener._timer.start(_get_refresh_seconds(category) * 1000)
	else:
		listener._timer.stop()


def _update_all_timers():
	for listener in list(_listeners):
		_update_refresh_timer(listener)


def _toggle(category):
	enabled = not _is_enabled(category)
	save_setting(SETTINGS_FILE, category.enabled_key, enabled)
	_update_all_timers()
	state = 'on' if enabled else 'off'
	message = '%s folder refresh: %s' % (category.label, state)
	if enabled:
		message += ' (every %d s)' % _get_refresh_seconds(category)
	show_status_message(message, timeout_secs=3)


class ToggleLocalFolderRefresh(ApplicationCommand):
	aliases = ('Toggle local folder refresh',)

	def __call__(self):
		_toggle(LOCAL)


class ToggleNetworkFolderRefresh(ApplicationCommand):
	aliases = ('Toggle network folder refresh',)

	def __call__(self):
		_toggle(NETWORK)


class ToggleFtpFolderRefresh(ApplicationCommand):
	aliases = ('Toggle FTP folder refresh',)

	def __call__(self):
		_toggle(FTP)
