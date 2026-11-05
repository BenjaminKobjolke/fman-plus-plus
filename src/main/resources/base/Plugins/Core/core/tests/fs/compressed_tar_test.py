from core.fs.compressed_tar import CompressedTarFileSystem, _DECOMPRESSED
from core.tests import StubFS
from fman.url import as_url, join, splitscheme
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import os
import tarfile


class CompressedTarFileSystemTest(TestCase):
	_SUFFIXES = {
		'.tar.gz': 'gz', '.tgz': 'gz',
		'.tar.bz2': 'bz2', '.tbz2': 'bz2', '.tbz': 'bz2',
		'.tar.xz': 'xz', '.txz': 'xz',
		'.tar.zst': 'zst', '.tzst': 'zst',
	}
	_FILE_CONTENTS = {
		'sub/dir1/file1.txt': b'file1\n',
		'sub/üȵĩöḋè/file.txt': b'file\n',
	}

	def setUp(self):
		super().setUp()
		self._tmp_dir = TemporaryDirectory()
		self._fs = CompressedTarFileSystem(StubFS(), set(self._SUFFIXES))
		self._fs._fs.add_child(self._fs)
		self._archives = {}
		for suffix, compression in self._SUFFIXES.items():
			archive = os.path.join(self._tmp_dir.name, 'archive' + suffix)
			self._write_archive(archive, compression)
			self._archives[suffix] = archive

	def tearDown(self):
		for archive in self._archives.values():
			zip_path = self._fs._split(self._path(archive))[0]
			entry = _DECOMPRESSED._entries.pop(zip_path, None)
			if entry is not None:
				entry.tmp_dir.cleanup()
		self._tmp_dir.cleanup()
		super().tearDown()

	def test_listing_and_metadata_for_every_suffix(self):
		for suffix, archive in self._archives.items():
			with self.subTest(suffix=suffix):
				self.assertEqual({'sub'}, set(self._fs.iterdir(self._path(archive))))
				self.assertEqual(
					{'dir1', 'empty', 'üȵĩöḋè'},
					set(self._fs.iterdir(self._path(archive, 'sub')))
				)
				self.assertEqual(
					[], list(self._fs.iterdir(self._path(archive, 'sub/empty')))
				)
				self.assertTrue(self._fs.is_dir(self._path(archive, 'sub/empty')))
				self.assertTrue(self._fs.exists(self._path(archive, 'sub')))
				self.assertEqual(
					len(self._FILE_CONTENTS['sub/dir1/file1.txt']),
					self._fs.size_bytes(self._path(archive, 'sub/dir1/file1.txt'))
				)

	def test_copy_out_and_all_writes_are_refused(self):
		for suffix, archive in self._archives.items():
			with self.subTest(suffix=suffix), TemporaryDirectory() as output_dir:
				before = Path(archive).read_bytes()
				destination = Path(output_dir, 'file.txt')
				self._fs.copy(
					self._url(archive, 'sub/dir1/file1.txt'), as_url(str(destination))
				)
				self.assertEqual(b'file1\n', destination.read_bytes())

				source = Path(output_dir, 'new.txt')
				source.write_bytes(b'new contents')
				with self.assertRaises(PermissionError):
					self._run_task(self._fs.prepare_copy(
						as_url(str(source)), self._url(archive, 'sub/new.txt')
					)[0])
				with self.assertRaises(PermissionError):
					self._fs.mkdir(self._path(archive, 'sub/newdir'))
				with self.assertRaises(PermissionError):
					self._fs.delete(self._path(archive, 'sub/dir1/file1.txt'))
				with self.assertRaises(PermissionError):
					self._run_task(self._fs.prepare_move(
						self._url(archive, 'sub/dir1/file1.txt'),
						self._url(archive, 'sub/renamed.txt')
					)[0])
				with self.assertRaises(PermissionError):
					self._run_task(self._fs.prepare_move(
						self._url(archive, 'sub/dir1/file1.txt'),
						as_url(str(Path(output_dir, 'moved.txt')))
					)[0])
				self.assertEqual(before, Path(archive).read_bytes())

	def test_archive_change_replaces_cached_decompressed_copy(self):
		suffix = '.tar.xz'
		archive = self._archives[suffix]
		self.assertEqual(
			{'sub'}, set(self._fs.iterdir(self._path(archive)))
		)
		zip_path = self._fs._split(self._path(archive))[0]
		old_entry = _DECOMPRESSED._entries[zip_path]
		self._write_archive(archive, 'xz', {'replacement/file.txt': b'new\n'})
		os.utime(archive, ns=(old_entry.stat_key[1] + 2_000_000_000,) * 2)
		self.assertEqual(
			{'replacement'}, set(self._fs.iterdir(self._path(archive)))
		)
		self.assertIsNot(old_entry, _DECOMPRESSED._entries[zip_path])

	def test_longest_suffix_is_used_when_splitting_tbz2(self):
		fs = CompressedTarFileSystem(StubFS(), {'.tbz', '.tbz2'})
		self.assertEqual(
			('x.tbz2', 'sub'), fs._split('x.tbz2/sub')
		)

	def test_corrupt_archive_does_not_leave_cached_copy(self):
		archive = os.path.join(self._tmp_dir.name, 'bad.tar.xz')
		Path(archive).write_bytes(b'not a compressed archive')
		with self.assertRaises(Exception):
			list(self._fs.iterdir(self._path(archive)))
		zip_path = self._fs._split(self._path(archive))[0]
		self.assertNotIn(zip_path, _DECOMPRESSED._entries)

	def _write_archive(self, archive, compression, files=None):
		files = self._FILE_CONTENTS if files is None else files
		with tarfile.open(archive, 'w:' + compression) as tar:
			directories = {'/'.join(name.split('/')[:index]) + '/'
				for name in files for index in range(1, len(name.split('/')))}
			if files is self._FILE_CONTENTS:
				directories.add('sub/empty/')
			for directory in sorted(directories):
				info = tarfile.TarInfo(directory)
				info.type = tarfile.DIRTYPE
				tar.addfile(info)
			for name, contents in files.items():
				info = tarfile.TarInfo(name)
				info.size = len(contents)
				tar.addfile(info, BytesIO(contents))

	def _run_task(self, task):
		task()

	def _url(self, archive, path=''):
		url = as_url(archive, 'ctar://')
		return join(url, path) if path else url

	def _path(self, archive, path=''):
		return splitscheme(self._url(archive, path))[1]
