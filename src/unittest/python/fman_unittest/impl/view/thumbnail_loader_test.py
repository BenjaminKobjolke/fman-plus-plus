from fman.impl.view.thumbnail_loader import load_image_thumbnail
from fman.url import as_url
from io import BytesIO
from pathlib import Path
from PyQt5.QtCore import QBuffer, QIODevice
from PyQt5.QtGui import QImage
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch


class ThumbnailLoaderTest(TestCase):

	def _image_bytes(self):
		image = QImage(400, 200, QImage.Format_RGB32)
		image.fill(0xff336699)
		buffer = QBuffer()
		buffer.open(QIODevice.WriteOnly)
		self.assertTrue(image.save(buffer, 'PNG'))
		return bytes(buffer.data())

	def test_local_image_is_scaled_with_aspect_ratio_preserved(self):
		with TemporaryDirectory() as directory:
			path = Path(directory, 'image.png')
			path.write_bytes(self._image_bytes())

			image = load_image_thumbnail(as_url(str(path)), 100)

		self.assertIsNotNone(image)
		self.assertEqual((100, 50), (image.width(), image.height()))

	def test_non_local_image_is_opened_through_fman_filesystem(self):
		with patch(
			'fman.impl.view.thumbnail_loader.fs.open',
			return_value=BytesIO(self._image_bytes()),
		) as open_file:
			image = load_image_thumbnail('zip://C:/images.zip/photo.png', 100)

		open_file.assert_called_once_with('zip://C:/images.zip/photo.png', 'rb')
		self.assertIsNotNone(image)
		self.assertEqual((100, 50), (image.width(), image.height()))

	def test_corrupt_image_returns_none(self):
		with patch(
			'fman.impl.view.thumbnail_loader.fs.open',
			return_value=BytesIO(b'not an image'),
		):
			self.assertIsNone(load_image_thumbnail('zip://archive/photo.png', 100))

	def test_missing_local_image_returns_none(self):
		self.assertIsNone(load_image_thumbnail('file://C:/missing/photo.png', 100))
