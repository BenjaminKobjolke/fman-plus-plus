from fman import PLATFORM
from fman.impl.model.shell_icons import ShellIconProvider
from pathlib import Path
from PyQt5.QtCore import QFileInfo, QSize
from PyQt5.QtWidgets import QApplication
from shutil import copyfile
from tempfile import TemporaryDirectory
from threading import Thread
from unittest import TestCase, skipIf
import sys

_APP = QApplication.instance() or QApplication([])

@skipIf(PLATFORM != 'Windows', 'Windows shell icons are platform-specific')
class ShellIconProviderTest(TestCase):

	def test_regular_files_share_an_icon_per_extension(self):
		with TemporaryDirectory() as directory:
			first = Path(directory, 'first.txt')
			second = Path(directory, 'second.txt')
			first.touch()
			second.touch()
			provider = ShellIconProvider()

			self.assertIs(
				provider.icon(QFileInfo(str(first))),
				provider.icon(QFileInfo(str(second)))
			)

	def test_executables_and_directories_keep_file_specific_icons(self):
		with TemporaryDirectory() as directory:
			first_exe = Path(directory, 'first.exe')
			second_exe = Path(directory, 'second.exe')
			copyfile(sys.executable, first_exe)
			copyfile(sys.executable, second_exe)
			first_dir = Path(directory, 'first')
			second_dir = Path(directory, 'second')
			first_dir.mkdir()
			second_dir.mkdir()
			provider = ShellIconProvider()

			self.assertIsNot(
				provider.icon(QFileInfo(str(first_exe))),
				provider.icon(QFileInfo(str(second_exe)))
			)
			self.assertIsNot(
				provider.icon(QFileInfo(str(first_dir))),
				provider.icon(QFileInfo(str(second_dir)))
			)

	def test_icon_has_materialized_standard_sizes(self):
		with TemporaryDirectory() as directory:
			file_path = Path(directory, 'file.txt')
			file_path.touch()
			icon = ShellIconProvider().icon(QFileInfo(str(file_path)))

		self.assertTrue(all(
			QSize(size, size) in icon.availableSizes()
			for size in (16, 32, 48)
		))

	def test_icon_can_be_fetched_and_rasterized_in_a_worker_thread(self):
		with TemporaryDirectory() as directory:
			file_path = Path(directory, 'file.txt')
			file_path.touch()
			provider = ShellIconProvider()
			result = []
			worker = Thread(target=lambda: result.append(
				provider.icon(QFileInfo(str(file_path))).pixmap(QSize(16, 16))
			))
			worker.start()
			worker.join()

		self.assertEqual(1, len(result))
		self.assertFalse(result[0].isNull())

