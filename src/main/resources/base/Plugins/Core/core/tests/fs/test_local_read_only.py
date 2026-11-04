from core import LocalFileSystem
from fman import PLATFORM
from fman.url import as_url
from pathlib import Path
import stat
from stat import S_IWRITE
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf
from unittest.mock import patch


@skipIf(PLATFORM != 'Windows', 'Read-only attributes are Windows-specific')
class LocalReadOnlyTest(TestCase):
	_READONLY_ATTRIBUTE = getattr(stat, 'FILE_ATTRIBUTE_READONLY', 1)

	def setUp(self):
		self._fs = LocalFileSystem()

	def test_copy_replaces_read_only_target_with_source_attributes(self):
		with TemporaryDirectory() as tmp_dir:
			src, dst = self._paths(tmp_dir)
			src.write_text('incoming')
			dst.write_text('old')
			self._make_read_only(dst)
			try:
				self._fs.copy(as_url(src), as_url(dst))
				self.assertEqual('incoming', dst.read_text())
				self.assertFalse(self._is_read_only(dst))
			finally:
				self._make_writable(src, dst)

	def test_copy_read_only_source_keeps_its_read_only_attribute(self):
		with TemporaryDirectory() as tmp_dir:
			src, dst = self._paths(tmp_dir)
			src.write_text('incoming')
			dst.write_text('old')
			self._make_read_only(src, dst)
			try:
				self._fs.copy(as_url(src), as_url(dst))
				self.assertEqual('incoming', dst.read_text())
				self.assertTrue(self._is_read_only(dst))
			finally:
				self._make_writable(src, dst)

	def test_same_drive_move_replaces_read_only_target(self):
		with TemporaryDirectory() as tmp_dir:
			src, dst = self._paths(tmp_dir)
			src.write_text('incoming')
			dst.write_text('old')
			self._make_read_only(dst)
			try:
				for task in self._fs._prepare_move(as_url(src), as_url(dst)):
					task()
				self.assertEqual('incoming', dst.read_text())
				self.assertFalse(src.exists())
			finally:
				self._make_writable(src, dst)

	def test_copy_move_path_replaces_read_only_target_and_deletes_source(self):
		with TemporaryDirectory() as tmp_dir:
			src, dst = self._paths(tmp_dir)
			src.write_text('incoming')
			dst.write_text('old')
			self._make_read_only(dst)
			try:
				for task in self._fs._prepare_move(
						as_url(src), as_url(dst), use_rename=False):
					task()
				self.assertEqual('incoming', dst.read_text())
				self.assertFalse(src.exists())
			finally:
				self._make_writable(src, dst)

	def test_failed_replace_restores_read_only_target_and_removes_partial(self):
		with TemporaryDirectory() as tmp_dir:
			src, dst = self._paths(tmp_dir)
			src.write_text('incoming')
			dst.write_text('old')
			partial = Path(str(dst) + '.fman-partial')
			self._make_read_only(dst)
			try:
				with patch(
					'core.fs.local.transfers.os.replace',
					side_effect=PermissionError(13, 'permission denied')
				):
					with self.assertRaises(PermissionError):
						self._fs.copy(as_url(src), as_url(dst))
				self.assertEqual('old', dst.read_text())
				self.assertTrue(self._is_read_only(dst))
				self.assertFalse(partial.exists())
			finally:
				self._make_writable(src, dst)

	@staticmethod
	def _paths(tmp_dir):
		return Path(tmp_dir, 'src'), Path(tmp_dir, 'dst')

	@staticmethod
	def _make_read_only(*paths):
		for path in paths:
			path.chmod(path.stat().st_mode & ~S_IWRITE)

	@staticmethod
	def _make_writable(*paths):
		for path in paths:
			if path.exists():
				path.chmod(path.stat().st_mode | S_IWRITE)

	@staticmethod
	def _is_read_only(path):
		return bool(
			path.stat().st_file_attributes & LocalReadOnlyTest._READONLY_ATTRIBUTE
		)
