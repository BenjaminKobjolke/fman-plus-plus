from core.fs.rar import RarFileSystem
from core.tests import StubFS
from datetime import date
from fman.url import as_url, join, splitscheme
from io import UnsupportedOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import hashlib
import os


class RarFileSystemTest(TestCase):
	_FIXTURES = ('rar3-subdirs.rar', 'rar5-subdirs.rar')
	_FILES = {
		'sub/dir1/file1.txt': (6, 'file1\n'),
		'sub/dir2/file2.txt': (6, 'file2\n'),
		'sub/with space/long fn.txt': (8, 'long fn\n'),
		'sub/üȵĩöḋè/file.txt': (5, 'file\n'),
	}

	def setUp(self):
		super().setUp()
		self._tmp_dir = TemporaryDirectory()
		self._archives = {}
		for fixture in self._FIXTURES:
			archive = os.path.join(self._tmp_dir.name, fixture)
			Path(archive).write_bytes(
				Path(os.path.dirname(__file__), fixture).read_bytes()
			)
			self._archives[fixture] = archive
		self._fs = RarFileSystem(StubFS(), {'.rar'})
		self._fs._fs.add_child(self._fs)

	def tearDown(self):
		self._tmp_dir.cleanup()
		super().tearDown()

	def test_fixture_hashes(self):
		expected = {
			'rar3-subdirs.rar': (
				'd3d4bd8c90b22fa01c11f460589499de06f9d28e076e'
				'c3762eea738c0903e874'
			),
			'rar5-subdirs.rar': (
				'4449d0e82e09f52af23a11cd84904625de8b15beafcf7'
				'3e5c30dc3296beae0b2'
			),
		}
		for fixture, archive in self._archives.items():
			with self.subTest(fixture=fixture):
				self.assertEqual(expected[fixture], self._sha256(archive))

	def test_directory_listing_and_empty_directory(self):
		for fixture, archive in self._archives.items():
			with self.subTest(fixture=fixture):
				self.assertEqual(
					{'dir1', 'dir2', 'empty', 'with space', 'üȵĩöḋè'},
					set(self._fs.iterdir(self._path(archive, 'sub')))
				)
				self.assertEqual([], list(self._fs.iterdir(
					self._path(archive, 'sub/empty')
				)))

	def test_exists_size_date_and_unicode_path(self):
		for fixture, archive in self._archives.items():
			with self.subTest(fixture=fixture):
				self.assertTrue(self._fs.exists(self._path(archive, 'sub')))
				self.assertTrue(self._fs.is_dir(self._path(archive, 'sub/empty')))
				self.assertFalse(self._fs.is_dir(
					self._path(archive, 'sub/dir1/file1.txt')
				))
				for path, (size, _) in self._FILES.items():
					archive_path = self._path(archive, path)
					self.assertTrue(self._fs.exists(archive_path), path)
					self.assertEqual(
						size, self._fs.size_bytes(archive_path), path
					)
					self.assertEqual(
						date(2020, 7, 20),
						self._fs.modified_datetime(archive_path).date(), path
					)
				self.assertTrue(self._fs.exists(
					self._path(archive, 'sub/üȵĩöḋè/file.txt')
				))

	def test_extract_file_and_folder(self):
		for fixture, archive in self._archives.items():
			with self.subTest(fixture=fixture):
				with TemporaryDirectory() as output:
					file_dest = os.path.join(output, 'file.txt')
					self._fs.copy(
						self._url(archive, 'sub/dir1/file1.txt'),
						as_url(file_dest)
					)
					self.assertEqual('file1\n', Path(file_dest).read_text())
					folder_dest = os.path.join(output, 'folder')
					self._fs.copy(
						self._url(archive, 'sub/dir2'), as_url(folder_dest)
					)
					self.assertEqual(
						'file2\n', Path(folder_dest, 'file2.txt').read_text()
					)

	def test_copy_into_archive_is_refused_without_changing_it(self):
		for fixture, archive in self._archives.items():
			with self.subTest(fixture=fixture):
				before = Path(archive).read_bytes()
				with TemporaryDirectory() as source_dir:
					source = Path(source_dir, 'new.txt')
					source.write_text('new contents')
					tasks = self._fs.prepare_copy(
						as_url(source), self._url(archive, 'sub/new.txt')
					)
					self.assertEqual(1, len(tasks))
					with self.assertRaises(PermissionError):
						tasks[0]()
				self.assertEqual(before, Path(archive).read_bytes())

	def test_moves_into_and_out_of_archive_are_refused_without_data_loss(self):
		for fixture, archive in self._archives.items():
			with self.subTest(fixture=fixture):
				before = Path(archive).read_bytes()
				with TemporaryDirectory() as source_dir:
					source = Path(source_dir, 'new.txt')
					source.write_text('new contents')
					tasks = self._fs.prepare_move(
						as_url(source), self._url(archive, 'sub/new.txt')
					)
					with self.assertRaises(PermissionError):
						tasks[0]()
					self.assertTrue(source.exists())
				self.assertEqual(before, Path(archive).read_bytes())

				output = os.path.join(self._tmp_dir.name, fixture + '.out')
				tasks = self._fs.prepare_move(
					self._url(archive, 'sub/dir1/file1.txt'), as_url(output)
				)
				with self.assertRaises(PermissionError):
					tasks[0]()
				self.assertEqual(before, Path(archive).read_bytes())
				self.assertFalse(Path(output).exists())

	def test_mkdir_and_delete_are_refused(self):
		archive = self._archives[self._FIXTURES[0]]
		with self.assertRaises(PermissionError):
			self._fs.mkdir(self._url(archive, 'sub/newdir').split('://', 1)[1])
		with self.assertRaises(PermissionError):
			self._fs.delete(
				self._url(archive, 'sub/dir1/file1.txt').split('://', 1)[1]
			)
		with self.assertRaises(UnsupportedOperation):
			self._fs.prepare_delete(
				self._url(archive, 'sub/dir1/file1.txt').split('://', 1)[1]
			)

	def _url(self, archive, path=''):
		return join(as_url(archive, 'rar://'), path) if path else as_url(
			archive, 'rar://'
		)

	def _path(self, archive, path=''):
		return splitscheme(self._url(archive, path))[1]

	def _sha256(self, path):
		return hashlib.sha256(Path(path).read_bytes()).hexdigest()
