import os
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf
from unittest.mock import patch

from fman import PLATFORM
from fman.url import as_url, splitscheme

from core import LocalFileSystem
from core.fs.local import wsl_links


@skipIf(PLATFORM != 'Windows', 'WSL reparse points are Windows-only')
class WslLinksTest(TestCase):
	def setUp(self):
		self._fs = LocalFileSystem()

	def test_stat_treats_wsl_link_as_non_directory(self):
		with TemporaryDirectory() as tmp_dir:
			link = _create_wsl_link(Path(tmp_dir, 'python3'))

			self.assertEqual(0, self._fs.stat(_urlpath(link)).st_size)
			self.assertFalse(self._fs.is_dir(_urlpath(link)))
			self.assertEqual(0, self._fs.size_bytes(_urlpath(link)))

	def test_copy_directory_preserves_wsl_link_and_regular_file(self):
		with TemporaryDirectory() as tmp_dir:
			src = Path(tmp_dir, 'src')
			bin_dir = src / 'bin'
			bin_dir.mkdir(parents=True)
			link = _create_wsl_link(bin_dir / 'python3')
			(bin_dir / 'activate').write_text('activate')
			dst = Path(tmp_dir, 'dst')

			self._fs.copy(as_url(src), as_url(dst))

			copied_link = dst / 'bin' / 'python3'
			self.assertEqual('activate', (dst / 'bin' / 'activate').read_text())
			self.assertEqual(
				wsl_links.IO_REPARSE_TAG_LX_SYMLINK,
				os.lstat(copied_link).st_reparse_tag
			)
			self.assertEqual(
				wsl_links.read_reparse_data(link),
				wsl_links.read_reparse_data(copied_link)
			)
			self.assertFalse(Path(str(copied_link) + '.fman-partial').exists())

	def test_copy_replaces_existing_destination_with_wsl_link(self):
		with TemporaryDirectory() as tmp_dir:
			src = _create_wsl_link(Path(tmp_dir, 'src'))
			dst = Path(tmp_dir, 'dst')
			dst.write_text('old destination')

			self._fs.copy(as_url(src), as_url(dst))

			self.assertEqual(
				wsl_links.IO_REPARSE_TAG_LX_SYMLINK,
				os.lstat(dst).st_reparse_tag
			)
			self.assertEqual(
				wsl_links.read_reparse_data(src), wsl_links.read_reparse_data(dst)
			)

	def test_move_directory_preserves_wsl_link(self):
		with TemporaryDirectory() as tmp_dir:
			src = Path(tmp_dir, 'src')
			src.mkdir()
			_create_wsl_link(src / 'python3')
			dst = Path(tmp_dir, 'dst')

			self._fs.move(as_url(src), as_url(dst))

			self.assertFalse(src.exists())
			self.assertEqual(
				wsl_links.IO_REPARSE_TAG_LX_SYMLINK,
				os.lstat(dst / 'python3').st_reparse_tag
			)

	def test_delete_directory_containing_wsl_link(self):
		with TemporaryDirectory() as tmp_dir:
			directory = Path(tmp_dir, 'directory')
			directory.mkdir()
			_create_wsl_link(directory / 'python3')

			self._fs.delete(_urlpath(directory))

			self.assertFalse(directory.exists())

	def test_copy_failure_removes_destination_and_partial_file(self):
		with TemporaryDirectory() as tmp_dir:
			src = _create_wsl_link(Path(tmp_dir, 'src'))
			dst = Path(tmp_dir, 'dst')
			partial = Path(str(dst) + '.fman-partial')
			with patch.object(
				wsl_links, 'write_reparse_data', side_effect=OSError('write failed')
			):
				with self.assertRaises(OSError):
					self._fs.copy(as_url(src), as_url(dst))

			self.assertFalse(dst.exists())
			self.assertFalse(partial.exists())


def _create_wsl_link(path: Path) -> Path:
	path.touch()
	payload = b'\x02\x00\x00\x00/usr/bin/python3'
	data = struct.pack('<IHH', wsl_links.IO_REPARSE_TAG_LX_SYMLINK, len(payload), 0)
	wsl_links.write_reparse_data(path, data + payload)
	return path


def _urlpath(path: Path) -> str:
	return splitscheme(as_url(path))[1]
