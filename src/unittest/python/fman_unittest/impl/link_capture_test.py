"""Tests for safely capturing external links in automation sessions."""

from unittest import TestCase
from unittest.mock import patch

from PyQt5.QtCore import QObject, QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QApplication

from fman.impl.scripting.link_capture import LinkCapture
from fman.impl.widgets import MainWindow


class LinkCaptureTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def test_http_and_https_urls_are_captured_without_opening_a_browser(self):
		capture = LinkCapture(_MainWindow())
		capture.install()
		self.addCleanup(capture.uninstall)

		for value in ('https://example.test/help/', 'http://example.test/about'):
			with self.subTest(url=value):
				self.assertTrue(QDesktopServices.openUrl(QUrl(value)))
		self.assertEqual([
			'https://example.test/help/', 'http://example.test/about',
		], capture.snapshot()['opened_urls'])

	def test_install_and_uninstall_register_only_web_schemes(self):
		capture = LinkCapture(_MainWindow())
		with patch.object(QDesktopServices, 'setUrlHandler') as set_handler, \
			patch.object(QDesktopServices, 'unsetUrlHandler') as unset_handler:
			capture.install()
			capture.uninstall()
		self.assertEqual(['http', 'https'], [
			call.args[0] for call in set_handler.call_args_list])
		self.assertEqual(['http', 'https'], [
			call.args[0] for call in unset_handler.call_args_list])

	def test_file_urls_are_not_recorded(self):
		capture = LinkCapture(_MainWindow())
		file_handler = _FileUrlHandler()
		capture.install()
		QDesktopServices.setUrlHandler('file', file_handler, 'ignore')
		self.addCleanup(QDesktopServices.unsetUrlHandler, 'file')
		self.addCleanup(capture.uninstall)

		self.assertTrue(QDesktopServices.openUrl(QUrl('file:///tmp/example.txt')))
		self.assertEqual([], capture.snapshot()['opened_urls'])

	def test_recent_opened_urls_are_limited_to_fifty(self):
		capture = LinkCapture(_MainWindow())
		for index in range(51):
			capture.record(QUrl('https://example.test/%d' % index))
		self.assertEqual(50, len(capture.snapshot()['opened_urls']))
		self.assertEqual('https://example.test/1',
			capture.snapshot()['opened_urls'][0])
		self.assertEqual('https://example.test/50',
			capture.snapshot()['opened_urls'][-1])

	def test_snapshot_extracts_links_from_recent_status_messages(self):
		window = _MainWindow([
			'v1 ready.',
			'Updated to v2. <a href="https://x.test/releases">Changelog</a>',
		])
		self.assertEqual([
			{'text': 'v1 ready.', 'links': []},
			{
				'text': window.messages[1],
				'links': ['https://x.test/releases'],
			},
		], LinkCapture(window).snapshot()['status_messages'])

	def test_main_window_keeps_only_the_twenty_recent_status_messages(self):
		window = MainWindow(None, [], None, None, None, None)
		self.addCleanup(window.deleteLater)
		for index in range(25):
			window.show_status_message('message %d' % index)
		self.assertEqual(
			['message %d' % index for index in range(5, 25)],
			window.get_status_history(),
		)


class _MainWindow:
	def __init__(self, messages=()):
		self.messages = list(messages)

	def get_status_history(self):
		return self.messages


class _FileUrlHandler(QObject):
	@pyqtSlot(QUrl)
	def ignore(self, url):
		pass
