"""Capture external URLs and recent status messages for automation sessions."""

from collections import deque
import re

from PyQt5.QtCore import QObject, QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices

from fman.impl.util.qt.thread import run_in_main_thread


URL_SCHEMES = ('http', 'https')
MAX_OPENED_URLS = 50
MAX_STATUS_MESSAGES = 20
_HREF_PATTERN = re.compile(r'href="([^"]+)"')


class LinkCapture(QObject):
	"""Keep web links opened by an isolated automation instance for inspection."""

	def __init__(self, main_window):
		super().__init__()
		self._main_window = main_window
		self._opened_urls = deque(maxlen=MAX_OPENED_URLS)

	def install(self):
		for scheme in URL_SCHEMES:
			QDesktopServices.setUrlHandler(scheme, self, 'record')

	def uninstall(self):
		for scheme in URL_SCHEMES:
			QDesktopServices.unsetUrlHandler(scheme)

	@pyqtSlot(QUrl)
	def record(self, url):
		self._opened_urls.append(url.toString())

	@run_in_main_thread
	def snapshot(self):
		status_history = self._main_window.get_status_history()
		return {
			'opened_urls': list(self._opened_urls),
			'status_messages': [
				{
					'text': text,
					'links': _HREF_PATTERN.findall(text),
				}
				for text in status_history[-MAX_STATUS_MESSAGES:]
			],
		}
