from fman.impl.view.thumbnail_cache import ThumbnailCache
from fman.impl.view.thumbnail_settings import ThumbnailSettings
from fman.url import as_url
from pathlib import Path
from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase
from unittest.mock import patch


class ThumbnailCacheTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls._app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.directory = TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		self.cache = ThumbnailCache(
			ThumbnailSettings(size=100, image_extensions=('.png',)),
			max_entries=2,
		)
		self.addCleanup(self.cache.clear)

	def _image(self, name, width=400, height=200):
		path = Path(self.directory.name, name)
		image = QImage(width, height, QImage.Format_RGB32)
		image.fill(0xff336699)
		self.assertTrue(image.save(str(path), 'PNG'))
		return as_url(str(path))

	def _request_and_wait(self, urls, count=1):
		loop = QEventLoop()
		received = []
		def on_ready(url):
			received.append(url)
			if len(received) >= count:
				loop.quit()
		self.cache.ready.connect(on_ready)
		QTimer.singleShot(3000, loop.quit)
		self.cache.request(urls)
		loop.exec_()
		self.cache.ready.disconnect(on_ready)
		return received

	def test_request_loads_preview_asynchronously_with_aspect_ratio(self):
		url = self._image('wide.png')
		ready = self._request_and_wait([url])
		self.assertEqual([url], ready)
		pixmap = self.cache.get(url)
		self.assertIsNotNone(pixmap)
		self.assertEqual((100, 50), (pixmap.width(), pixmap.height()))

	def test_corrupt_image_completes_without_a_preview(self):
		path = Path(self.directory.name, 'corrupt.png')
		path.write_bytes(b'not an image')
		url = as_url(str(path))
		ready = self._request_and_wait([url])
		self.assertEqual([url], ready)
		self.assertIsNone(self.cache.get(url))

	def test_least_recently_used_entry_is_evicted(self):
		urls = [self._image(f'{index}.png') for index in range(3)]
		ready = self._request_and_wait(urls[:2], 2)
		self.assertCountEqual(urls[:2], ready)
		self.cache.get(urls[0])
		self.assertEqual([urls[2]], self._request_and_wait([urls[2]]))
		self.assertIsNotNone(self.cache.get(urls[0]))
		self.assertIsNone(self.cache.get(urls[1]))
		self.assertIsNotNone(self.cache.get(urls[2]))

	def test_size_change_clears_cached_preview_and_reloads_at_new_size(self):
		url = self._image('resize.png')
		ready = self._request_and_wait([url])
		self.assertEqual([url], ready)
		self.assertEqual(100, self.cache.get(url).width())

		self.cache.set_settings(ThumbnailSettings(
			size=50, image_extensions=('.png',),
		))
		self.assertIsNone(self.cache.get(url))
		ready = self._request_and_wait([url])
		self.assertEqual([url], ready)
		self.assertEqual((50, 25), (
			self.cache.get(url).width(), self.cache.get(url).height(),
		))

	def test_clear_drops_thumbnails_still_queued_for_previous_folder(self):
		urls = [self._image(f'queued-{index}.png') for index in range(3)]
		started = Event()
		release = Event()
		loaded = []
		def load(url, size):
			loaded.append(url)
			if len(loaded) == 2:
				started.set()
			release.wait(2)
			return QImage(1, 1, QImage.Format_RGB32)

		with patch(
			'fman.impl.view.thumbnail_cache.load_image_thumbnail',
			side_effect=load,
		):
			self.cache.request(urls)
			self.assertTrue(started.wait(1))
			self.cache.clear()
			release.set()
			self.assertTrue(self.cache._pool.waitForDone(1000))

		self.assertEqual(2, len(loaded))
