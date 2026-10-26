"""Offer the latest GitHub release through the command palette or timer."""
import os
import sys
import tempfile
from subprocess import DEVNULL, Popen

from core import net
from core.updates import check_for_update
from fman import APP_NAME, ApplicationCommand, NO, PLATFORM, Task, YES, \
	clear_status_message, links, load_json, save_json, show_alert, \
	show_status_message, submit_task
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from urllib.error import HTTPError, URLError

__all__ = ['CheckForUpdates']

UPDATE_CHECK_FILE = 'Update Check.json'
CHECKING_MESSAGE = 'Checking for updates…'
UPDATE_MESSAGE = APP_NAME + ' %s is available (installed: %s). Open the download page?'
INSTALLER_ASSETS = {'Windows': 'fmanSetup.exe', 'Mac': 'fman.dmg'}
DOWNLOAD_URL = 'https://github.com/%s/releases/download/%s/%s'
INSTALL_MESSAGE = (
	APP_NAME + ' %s is available (installed: %s). '
	'Download and install it now?'
)
DOWNLOAD_ERROR = 'Could not download the update: %s'
CURRENT_MESSAGE = APP_NAME + ' %s is up to date.'
ERROR_MESSAGE = 'Could not check for updates: %s'


class CheckForUpdates(ApplicationCommand):
	aliases = ('Check for updates',)

	def __call__(self, silent=False):
		if not silent:
			show_status_message(CHECKING_MESSAGE)
		try:
			try:
				status = check_for_update()
			except (URLError, LookupError, ValueError, KeyError) as error:
				if not silent:
					show_alert(ERROR_MESSAGE % error)
				return
			if not status.update_available:
				if not silent:
					show_alert(CURRENT_MESSAGE % status.installed)
				return
			settings = load_json(UPDATE_CHECK_FILE, default={})
			if silent and settings.get('announced') == status.latest:
				return
			settings['announced'] = status.latest
			save_json(UPDATE_CHECK_FILE)
			message = (
				INSTALL_MESSAGE if PLATFORM in INSTALLER_ASSETS else UPDATE_MESSAGE
			)
			answer = show_alert(
				message % (status.latest, status.installed),
				YES | NO, YES
			)
			if answer & YES:
				_install(status.latest)
		finally:
			if not silent:
				clear_status_message()


def _install(latest):
	asset = INSTALLER_ASSETS.get(PLATFORM)
	if asset is None:
		QDesktopServices.openUrl(QUrl(links.RELEASES))
		return

	path = os.path.join(tempfile.gettempdir(), asset)
	if os.path.exists(path):
		os.remove(path)
	url = DOWNLOAD_URL % (links.GITHUB_REPO, latest, asset)
	error = []

	task = None

	def download_update():
		try:
			net.download(url, path, task)
		except (URLError, HTTPError, OSError) as e:
			error.append(e)

	task = Task('Downloading ' + asset, fn=download_update)
	submit_task(task)
	if error:
		show_alert(DOWNLOAD_ERROR % error[0])
		QDesktopServices.openUrl(QUrl(links.RELEASES))
		return
	if not os.path.exists(path):
		return

	if PLATFORM == 'Windows':
		Popen([path], cwd=os.path.dirname(path), stdout=DEVNULL, stderr=DEVNULL)
		sys.exit(0)
	else:
		Popen(['open', path])
