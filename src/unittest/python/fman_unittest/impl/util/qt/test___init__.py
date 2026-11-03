from fbs_runtime.platform import is_windows
from fman.impl.util.qt import as_qurl, from_qurl, get_urls, set_urls
from PyQt5.QtCore import QMimeData, QUrl
from unittest import TestCase

class AsFromQurlTest(TestCase):
	def test_file_url(self):
		url = 'file://C:/test' if is_windows() else 'file:///test'
		self._check(url)
	def test_zip_url(self):
		url = 'zip://C:/test.zip' if is_windows() else 'zip:///test.zip'
		self._check(url)
	def test_ftp(self):
		self._check('ftp://user:pass@123.45.67.89/dir')
	def test_space_in_file_url(self):
		root = 'file://C:/test' if is_windows() else 'file:///test'
		self._check(root + '/a and b.txt')
	def test_space_in_ftp_url(self):
		self._check('ftp:///a and b.txt')
	def test_space_in_other_url(self):
		self._check('other:///a and b.txt')
	def _check(self, url):
		self.assertEqual(url, from_qurl(as_qurl(url)))

class UrlMimeDataTest(TestCase):
	def test_set_urls_and_get_urls_preserve_original_urls(self):
		urls = [
			'ftp://XIDA Projects/a/b.txt',
			'ftps://duran Server FTP/x',
			'file:///test/a.txt'
		]
		mime_data = QMimeData()

		set_urls(mime_data, urls)

		self.assertEqual(urls, get_urls(mime_data))

	def test_get_urls_falls_back_to_qt_urls(self):
		mime_data = QMimeData()
		mime_data.setUrls([as_qurl('ftp://kobjolke.com/a')])

		self.assertEqual(['ftp://kobjolke.com/a'], get_urls(mime_data))

	def test_get_urls_skips_invalid_qt_urls(self):
		mime_data = QMimeData()
		mime_data.setUrls([QUrl('')])

		self.assertEqual([], get_urls(mime_data))
