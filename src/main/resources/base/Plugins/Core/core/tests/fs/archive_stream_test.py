from core.fs.compressed_tar import CompressedTarFileSystem
from core.fs.rar import RarFileSystem
from core.fs.zip import ZipFileSystem
from core.tests import StubFS
from fman.fs import FileSystem
from fman.impl.plugins.mother_fs import MotherFileSystem
from fman.url import as_url
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from shutil import copyfile
from zipfile import ZipFile

import os

class ArchiveStreamTest(TestCase):
	def setUp(self):
		self._tmp_dir = TemporaryDirectory()
		self._zip_path = os.path.join(self._tmp_dir.name, 'sample.zip')
		copyfile(
			os.path.join(os.path.dirname(__file__), 'ZipFileSystemTest.zip'),
			self._zip_path
		)
		self._mother_fs = MotherFileSystem(None)
		self._local_fs = StubFS()._backends['file://']
		self._mother_fs.add_child('file://', self._local_fs)
		self._memory_fs = MemoryFileSystem()
		self._mother_fs.add_child('mem://', self._memory_fs)
		self._zip_fs = ZipFileSystem(self._mother_fs, {'.zip'})
		self._mother_fs.add_child('zip://', self._zip_fs)
		self._zip_url = as_url(self._zip_path, 'zip://')

	def tearDown(self):
		self._tmp_dir.cleanup()

	def test_read_entry_extracts_to_temp_and_cleans_up_on_close(self):
		with ZipFile(self._zip_path) as archive:
			expected = archive.read('ZipFileTest/file.txt')
		stream = self._zip_fs.open(self._zip_path + '/ZipFileTest/file.txt', 'rb')
		temp_path = Path(stream.name)
		self.assertEqual(expected, stream.read())
		self.assertTrue(temp_path.exists())
		stream.close()
		self.assertFalse(temp_path.exists())

	def test_read_directory_and_missing_entry_raise(self):
		with self.assertRaises(IsADirectoryError):
			self._zip_fs.open(self._zip_path + '/ZipFileTest/Directory', 'rb')
		with self.assertRaises(FileNotFoundError):
			self._zip_fs.open(self._zip_path + '/missing.txt', 'rb')

	def test_write_requires_existing_archive_parent_and_binary_mode(self):
		with self.assertRaises(FileNotFoundError):
			self._zip_fs.open(self._zip_path + '/missing/new.txt', 'wb')
		with self.assertRaises(ValueError):
			self._zip_fs.open(self._zip_path + '/ZipFileTest/file.txt', 'r')

	def test_write_adds_and_overwrites_archive_entry_on_close(self):
		with self._zip_fs.open(self._zip_path + '/ZipFileTest/new.txt', 'wb') as stream:
			stream.write(b'new')
		with self._zip_fs.open(self._zip_path + '/ZipFileTest/new.txt', 'rb') as stream:
			self.assertEqual(b'new', stream.read())
		with self._zip_fs.open(self._zip_path + '/ZipFileTest/new.txt', 'wb') as stream:
			stream.write(b'replaced')
		with self._zip_fs.open(self._zip_path + '/ZipFileTest/new.txt', 'rb') as stream:
			self.assertEqual(b'replaced', stream.read())

	def test_exception_while_writing_leaves_archive_unchanged_and_cleans_temp(self):
		before = Path(self._zip_path).read_bytes()
		stream = self._zip_fs.open(self._zip_path + '/ZipFileTest/new.txt', 'wb')
		temp_path = Path(stream.name)
		with self.assertRaisesRegex(RuntimeError, 'caller failed'):
			with stream:
				stream.write(b'partial')
				raise RuntimeError('caller failed')
		self.assertEqual(before, Path(self._zip_path).read_bytes())
		self.assertFalse(temp_path.exists())

	def test_read_only_rar_and_compressed_tar_refuse_write(self):
		rar_path = os.path.join(
			os.path.dirname(__file__), 'rar3-subdirs.rar'
		)
		rar_fs = RarFileSystem(StubFS(), {'.rar'})
		tar_fs = CompressedTarFileSystem(StubFS(), {'.tar.gz'})
		for fs, url in (
			(rar_fs, rar_path.replace(os.sep, '/') + '/sub/dir1/file1.txt'),
			(tar_fs, 'archive.tar.gz/file.txt'),
		):
			with self.subTest(path=url), self.assertRaises(PermissionError):
				fs.open(url, 'wb')

	def test_prepare_copy_streams_files_and_folders_between_memory_and_zip(self):
		self._memory_fs.files.update({
			'folder': None,
			'folder/one.txt': b'one',
			'folder/two.txt': b'two',
		})
		for task in self._mother_fs.prepare_copy(
			'mem://folder', self._zip_url + '/ZipFileTest/from-memory'
		):
			task()
		with self._zip_fs.open(
			self._zip_path + '/ZipFileTest/from-memory/one.txt', 'rb'
		) as stream:
			self.assertEqual(b'one', stream.read())
		for task in self._mother_fs.prepare_copy(
			self._zip_url + '/ZipFileTest/Directory', 'mem://from-zip'
		):
			task()
		with ZipFile(self._zip_path) as archive:
			self.assertEqual(
				archive.read('ZipFileTest/Directory/file 2.txt'),
				self._memory_fs.files['from-zip/file 2.txt']
			)
			self.assertEqual(
				archive.read('ZipFileTest/Directory/Subdirectory/file 3.txt'),
				self._memory_fs.files['from-zip/Subdirectory/file 3.txt']
			)


class MemoryFileSystem(FileSystem):
	scheme = 'mem://'

	def __init__(self):
		super().__init__()
		self.files = {}

	def exists(self, path):
		return path in self.files

	def is_dir(self, path):
		if path not in self.files:
			raise FileNotFoundError(path)
		return self.files[path] is None

	def iterdir(self, path):
		if not self.is_dir(path):
			raise NotADirectoryError(path)
		prefix = path + '/' if path else ''
		return [
			name[len(prefix):] for name in self.files
			if (
				name.startswith(prefix)
				and name[len(prefix):]
				and '/' not in name[len(prefix):]
			)
		]

	def mkdir(self, path):
		parent = path.rsplit('/', 1)[0] if '/' in path else ''
		if parent and not self.is_dir(parent):
			raise FileNotFoundError(parent)
		self.files[path] = None

	def open(self, path, mode):
		if mode == 'rb':
			if path not in self.files:
				raise FileNotFoundError(path)
			if self.files[path] is None:
				raise IsADirectoryError(path)
			return BytesIO(self.files[path])
		if mode != 'wb':
			raise ValueError(mode)
		return MemoryWriteStream(self, path)


class MemoryWriteStream(BytesIO):
	def __init__(self, fs, path):
		super().__init__()
		self._fs = fs
		self._path = path

	def close(self):
		if not self.closed:
			self._fs.files[self._path] = self.getvalue()
		super().close()
