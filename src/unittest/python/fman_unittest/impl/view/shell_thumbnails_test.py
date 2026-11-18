from fman import PLATFORM
from fman.impl.view.shell_thumbnails import shell_thumbnail
from pathlib import Path
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf

_APP = QApplication.instance() or QApplication([])


class ShellThumbnailsTest(TestCase):

	@skipIf(PLATFORM != 'Windows', 'Windows shell thumbnails are platform-specific')
	def test_reads_a_thumbnail_from_a_local_image(self):
		with TemporaryDirectory() as directory:
			path = Path(directory, 'image.png')
			image = QImage(100, 50, QImage.Format_RGB32)
			image.fill(0xff336699)
			self.assertTrue(image.save(str(path), 'PNG'))

			thumbnail = shell_thumbnail(str(path), 48)

		self.assertIsNotNone(thumbnail)
		self.assertLessEqual(max(thumbnail.width(), thumbnail.height()), 48)
