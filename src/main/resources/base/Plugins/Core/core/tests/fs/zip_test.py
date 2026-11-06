from errno import ENOENT
from core.fs import archive_password
from core.fs.zip import ZipFileSystem, SevenZipFileSystem, SEVEN_ZIP_BINARY
from core.fs.move_by_copy import MoveByCopy
import core.fs.zip as zip_module
from core.tests import StubFS
from datetime import date, datetime
from fman import Task
from fman.fs import FileSystem
from fman.url import as_url, join, as_human_readable, splitscheme
from os import listdir
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from unicodedata import normalize
from unittest import TestCase
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import os
import os.path
import subprocess

class MoveByCopyTest(TestCase):
	def setUp(self):
		self.fs = MagicMock(spec=FileSystem)
		self.src = 'zip://source.zip/item.txt'
		self.dst = 'file:///destination/item.txt'
		self.copy = Task('Copying item.txt')
		self.task = MoveByCopy(self.fs, self.src, self.dst, [self.copy])
	def _fail_copy(self):
		raise OSError('copy failed')
	def test_copy_failure_keeps_source(self):
		self.copy = Task('Copying item.txt', fn=self._fail_copy)
		self.task = MoveByCopy(self.fs, self.src, self.dst, [self.copy])
		with self.assertRaises(OSError):
			self.task()
		self.fs.delete.assert_not_called()
	def test_cancel_after_copy_keeps_source(self):
		with patch.object(self.task, 'check_canceled', side_effect=Task.Canceled):
			with self.assertRaises(Task.Canceled):
				self.task()
		self.fs.delete.assert_not_called()
	def test_missing_destination_keeps_source(self):
		self.fs.exists.return_value = False
		with self.assertRaises(OSError):
			self.task()
		self.fs.delete.assert_not_called()
	def test_success_deletes_source_after_copy_and_destination_check(self):
		calls = []
		self.copy = Task('Copying item.txt', fn=lambda: calls.append('copy'))
		self.fs.exists.side_effect = lambda url: calls.append(('exists', url)) or True
		self.fs.delete.side_effect = lambda url: calls.append(('delete', url))
		self.task = MoveByCopy(self.fs, self.src, self.dst, [self.copy])
		self.task()
		self.assertEqual([
			'copy', ('exists', self.dst), ('delete', self.src)
		], calls)
	def test_archive_to_archive_copy_failure_keeps_source(self):
		self.dst = 'zip://destination.zip/item.txt'
		self.copy = Task('Packing item.txt', fn=self._fail_copy)
		self.task = MoveByCopy(self.fs, self.src, self.dst, [self.copy])
		with self.assertRaises(OSError):
			self.task()
		self.fs.delete.assert_not_called()

class ZipFileSystemTest(TestCase):
	def test_extracting_password_protected_archives_prompts_once(self):
		for extension, scheme in (('.zip', 'zip://'), ('.7z', '7z://')):
			with self.subTest(extension=extension), TemporaryDirectory() as tmp_dir:
				archive_path = self._create_encrypted_archive(tmp_dir, extension)
				fs = self._filesystem_for(archive_path, extension)
				with patch.object(
					archive_password, 'ask_password', return_value='secret'
				) as ask_password:
					for name in ('one.txt', 'two.txt'):
						destination = os.path.join(tmp_dir, 'out-' + name)
						fs.copy(
							as_url(
								archive_path.replace(os.sep, '/') + '/' + name, scheme
							),
							as_url(destination),
						)
						self.assertEqual(name, Path(destination).read_text())
				ask_password.assert_called_once()
	def test_wrong_then_right_password_retries_without_leaving_partial_file(self):
		for extension in ('.zip', '.7z'):
			with self.subTest(extension=extension), TemporaryDirectory() as tmp_dir:
				archive_path = self._create_encrypted_archive(tmp_dir, extension)
				fs = self._filesystem_for(archive_path, extension)
				destination_dir = os.path.join(tmp_dir, 'destination')
				os.mkdir(destination_dir)
				destination = os.path.join(destination_dir, 'output.txt')
				with patch.object(
					archive_password, 'ask_password', side_effect=('wrong', 'secret')
				) as ask_password:
					fs.copy(
						self._archive_url(archive_path, 'one.txt', extension),
						as_url(destination),
					)
				self.assertEqual('one.txt', Path(destination).read_text())
				self.assertEqual(2, ask_password.call_count)
				self.assertFalse(ask_password.call_args_list[0].kwargs['wrong_password'])
				self.assertTrue(ask_password.call_args_list[1].kwargs['wrong_password'])
				self.assertEqual(['output.txt'], os.listdir(destination_dir))
				self.assertGreater(Path(destination).stat().st_size, 0)
	def test_cancelling_password_prompt_does_not_create_destination(self):
		for extension in ('.zip', '.7z'):
			with self.subTest(extension=extension), TemporaryDirectory() as tmp_dir:
				archive_path = self._create_encrypted_archive(tmp_dir, extension)
				fs = self._filesystem_for(archive_path, extension)
				destination = os.path.join(tmp_dir, 'output.txt')
				with patch.object(
					archive_password, 'ask_password', side_effect=Task.Canceled
				):
					with self.assertRaises(Task.Canceled):
						fs.copy(
							self._archive_url(archive_path, 'one.txt', extension),
							as_url(destination)
						)
				self.assertFalse(Path(destination).exists())
	def test_archive_additions_use_remembered_password_and_aes_for_zip(self):
		for extension in ('.zip', '.7z'):
			with self.subTest(extension=extension), TemporaryDirectory() as tmp_dir:
				archive_path = os.path.join(tmp_dir, 'protected' + extension)
				Path(tmp_dir, 'initial.txt').write_text('initial')
				if extension == '.zip':
					with ZipFile(archive_path, 'w') as archive:
						archive.write(Path(tmp_dir, 'initial.txt'), 'initial.txt')
				else:
					zip_module._run_7zip(
						['a', archive_path, 'initial.txt'], cwd=tmp_dir
					)
				fs = self._filesystem_for(archive_path, extension)
				archive_password.remember_password(archive_path, 'secret')
				source = Path(tmp_dir, 'added.txt')
				source.write_text('added')
				fs.copy(
					as_url(str(source)),
					self._archive_url(archive_path, 'added.txt', extension),
				)
				if extension == '.zip':
					output = subprocess.run(
						[SEVEN_ZIP_BINARY, 'l', '-slt', archive_path],
						check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
						text=True
					).stdout
					entry = output.split('Path = added.txt', 1)[1]
					self.assertIn('Method = AES-256', entry)
				with TemporaryDirectory() as extracted:
					destination = os.path.join(extracted, 'added.txt')
					with patch.object(
						archive_password, 'ask_password', return_value='secret'
					) as ask_password:
						fs.copy(
							self._archive_url(archive_path, 'added.txt', extension),
							as_url(destination)
						)
					self.assertEqual('added', Path(destination).read_text())
					ask_password.assert_not_called()
	def test_plain_archives_never_prompt_for_a_password(self):
		for extension in ('.zip', '.7z'):
			with self.subTest(extension=extension), TemporaryDirectory() as tmp_dir:
				archive_path = os.path.join(tmp_dir, 'plain' + extension)
				if extension == '.zip':
					with ZipFile(archive_path, 'w') as archive:
						archive.writestr('file.txt', 'plain')
				else:
					Path(tmp_dir, 'file.txt').write_text('plain')
					zip_module._run_7zip(
						['a', archive_path, 'file.txt'], cwd=tmp_dir
					)
				fs = self._filesystem_for(archive_path, extension)
				destination = os.path.join(tmp_dir, 'output.txt')
				with patch.object(archive_password, 'ask_password') as ask_password:
					fs.copy(
						self._archive_url(archive_path, 'file.txt', extension),
						as_url(destination)
					)
				self.assertEqual('plain', Path(destination).read_text())
				ask_password.assert_not_called()
	def _filesystem_for(self, archive_path, extension):
		if extension == '.7z':
			return SevenZipFileSystem(StubFS(), {extension})
		return self._fs
	def _archive_url(self, archive_path, path_in_archive, extension):
		scheme = '7z://' if extension == '.7z' else 'zip://'
		return as_url(archive_path.replace(os.sep, '/') + '/' + path_in_archive, scheme)
	def _create_encrypted_archive(self, tmp_dir, extension):
		archive_path = os.path.join(tmp_dir, 'protected' + extension)
		for name in ('one.txt', 'two.txt'):
			Path(tmp_dir, name).write_text(name)
		args = [SEVEN_ZIP_BINARY]
		if os.name == 'nt':
			args.append('-sccUTF-8')
		args.extend(['a', archive_path, 'one.txt', 'two.txt', '-p'])
		if extension == '.zip':
			args.append('-mem=AES256')
		result = subprocess.run(
			args, cwd=tmp_dir, input='secret\n', text=True,
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT
		)
		if result.returncode:
			self.fail('Could not create encrypted fixture: ' + result.stdout)
		return archive_path
	def test_7z_fractional_modified_timestamp(self):
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.7z')
			file_path = os.path.join(tmp_dir, 'file.txt')
			Path(file_path).write_text('contents')
			mtime = datetime.now().replace(microsecond=123456)
			os.utime(file_path, (mtime.timestamp(), mtime.timestamp()))
			zip_module._run_7zip(['a', zip_path, file_path])
			fs = SevenZipFileSystem(StubFS(), {'.7z'})
			self.assertEqual(
				date.today(), fs.modified_datetime(zip_path + '/file.txt').date()
			)
	def test_7z_follows_symlink_when_adding_on_non_windows(self):
		if os.name == 'nt':
			self.skipTest('This checks the non-Windows 7-Zip command line.')
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.7z')
			archive_file = zip_path + '/linked.txt'
			target = Path(tmp_dir, 'target.txt')
			target.write_text('target contents')
			link = Path(tmp_dir, 'link.txt')
			link.symlink_to(target)
			fs = SevenZipFileSystem(StubFS(), {'.7z'})
			fs.copy(as_url(link), as_url(archive_file, '7z://'))
			with TemporaryDirectory() as extract_dir:
				fs.copy(as_url(archive_file, '7z://'), as_url(
					os.path.join(extract_dir, 'linked.txt')
				))
				self.assertEqual(
					'target contents',
					Path(extract_dir, 'linked.txt').read_text()
				)
	def test_iterdir(self):
		self._expect_iterdir_result('', {'ZipFileTest'})
		self._expect_iterdir_result(
			'ZipFileTest',
			{'Directory', 'Empty directory', 'file.txt', 'ça va.txt'}
		)
		self._expect_iterdir_result(
			'ZipFileTest/Directory', {'Subdirectory', 'file 2.txt'}
		)
		self._expect_iterdir_result(
			'ZipFileTest/Directory/Subdirectory', {'file 3.txt'}
		)
		self._expect_iterdir_result('ZipFileTest/Empty directory', set())
	def test_iterdir_empty_zip(self):
		with TemporaryDirectory() as zip_container:
			zip_path = os.path.join(zip_container, 'test.zip')
			self._create_empty_zip(zip_path)
			self.assertEqual([], self._listdir(self._path('', zip_path)))
	def test_iterdir_sparse_zip(self):
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.zip')
			for depth in range(3):
				file_relpath = os.path.join(*(['dir'] * depth + ['file.txt']))
				with ZipFile(zip_path, 'w') as zip_file:
					zip_file.write(__file__, file_relpath)
				for level in range(depth):
					dir_path = self._path('/'.join(['dir'] * level), zip_path)
					self.assertEqual(
						['dir'], self._listdir(dir_path),
						'Failed at nesting level ' + file_relpath
					)
	def test_iterdir_nonexistent_zip(self):
		with self.assertRaises(FileNotFoundError):
			self._listdir('nonexistent.zip')
	def test_iterdir_nonexistent_path_in_zip(self):
		with self.assertRaises(FileNotFoundError):
			self._listdir(self._path('nonexistent'))
	def _listdir(self, zip_urlpath):
		return list(self._fs.iterdir(zip_urlpath))
	def test_is_dir(self):
		for dir_ in self._dirs_in_zip:
			self.assertTrue(self._fs.is_dir(self._path(dir_)), dir_)
		for nondir in self._files_in_zip:
			self.assertFalse(self._fs.is_dir(self._path(nondir)), nondir)
		for nonexistent in ('nonexistent', 'ZipFileTest/nonexistent'):
			with self.assertRaises(FileNotFoundError):
				self._fs.is_dir(self._path(nonexistent)), nonexistent
	def test_exists(self):
		for existent in self._dirs_in_zip + self._files_in_zip:
			self.assertTrue(self._fs.exists(self._path(existent)), existent)
		for nonexistent in ('nonexistent', 'ZipFileTest/nonexistent'):
			self.assertFalse(
				self._fs.exists(self._path(nonexistent)), nonexistent
			)
	def test_extract_entire_zip(self):
		self._test_extract_dir('')
	def _test_extract_dir(self, path_in_zip):
		expected_files = self._get_zip_contents(path_in_zip=path_in_zip)
		with TemporaryDirectory() as tmp_dir:
			# Create a subdirectory because the destination directory of a copy
			# operation must not yet exist:
			dst_dir = os.path.join(tmp_dir, 'dest')
			self._fs.copy(self._url(path_in_zip), as_url(dst_dir))
			self.assertEqual(expected_files, self._read_directory(dst_dir))
	def test_extract_subdir(self):
		self._test_extract_dir('ZipFileTest/Directory')
	def test_extract_empty_directory(self):
		self._test_extract_dir('ZipFileTest/Empty directory')
	def test_extract_file(self):
		with TemporaryDirectory() as tmp_dir:
			file_path = 'ZipFileTest/file.txt'
			dest_path = os.path.join(tmp_dir, 'file.txt')
			self._fs.copy(self._url(file_path), as_url(dest_path))
			self.assertEqual(['file.txt'], listdir(tmp_dir))
			expected_contents = self._get_zip_contents(path_in_zip=file_path)
			with open(dest_path) as f:
				self.assertEqual(expected_contents, f.read())
	def test_extract_nonexistent(self):
		with self.assertRaises(FileNotFoundError):
			with TemporaryDirectory() as tmp_dir:
				self._fs.copy(self._url('nonexistent'), as_url(tmp_dir))
	def test_add_file(self):
		with TemporaryDirectory() as tmp_dir:
			file_to_add = os.path.join(tmp_dir, 'tmp.txt')
			file_contents = 'added!'
			with open(file_to_add, 'w') as f:
				f.write(file_contents)
			dest_url_in_zip = self._url('ZipFileTest/Directory/added.txt')
			self._fs.copy(as_url(file_to_add), dest_url_in_zip)
			dest_url = join(as_url(tmp_dir), 'extracted.txt')
			self._fs.copy(dest_url_in_zip, dest_url)
			with open(as_human_readable(dest_url)) as f:
				actual_contents = f.read()
			self.assertEqual(file_contents, actual_contents)
	def test_add_directory(self):
		with TemporaryDirectory() as zip_contents:
			with ZipFile(self._zip) as zip_file:
				zip_file.extractall(zip_contents)
			with TemporaryDirectory() as zip_container:
				zip_path = os.path.join(zip_container, 'test.zip')
				self._create_empty_zip(zip_path)
				self._fs.copy(
					as_url(os.path.join(zip_contents, 'ZipFileTest')),
					join(as_url(zip_path, 'zip://'), 'ZipFileTest')
				)
				self._expect_zip_contents(self._get_zip_contents(), zip_path)
	def test_replace_file(self):
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.zip')
			some_file = os.path.join(tmp_dir, 'tmp.txt')
			with open(some_file, 'w') as f:
				f.write('added!')
			with ZipFile(zip_path, 'w') as zip_file:
				zip_file.write(some_file, 'tmp.txt')
			expected_contents = b'replaced!'
			with open(some_file, 'wb') as f:
				f.write(expected_contents)
			dest_url_in_zip = join(as_url(zip_path, 'zip://'), 'tmp.txt')
			self._fs.copy(as_url(some_file), dest_url_in_zip)
			with ZipFile(zip_path) as zip_file:
				# A primitive implementation would have two 'tmp.txt' entries:
				self.assertEqual(['tmp.txt'], zip_file.namelist())
				with zip_file.open('tmp.txt') as f_in_zip:
					self.assertEqual(expected_contents, f_in_zip.read())
	def test_mkdir(self):
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.zip')
			self._create_empty_zip(zip_path)
			self._fs.mkdir(splitscheme(as_url(zip_path, 'zip://'))[1] + '/dir')
			self._expect_zip_contents({'dir': {}}, zip_path)
	def test_mkdir_raises_fileexistserror(self):
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.zip')
			self._create_empty_zip(zip_path)
			dir_url_path = splitscheme(as_url(zip_path, 'zip://'))[1] + '/dir'
			self._fs.mkdir(dir_url_path)
			with self.assertRaises(FileExistsError):
				self._fs.mkdir(dir_url_path)
	def test_mkdir_raises_filenotfounderror(self):
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.zip')
			self._create_empty_zip(zip_path)
			zip_url_path = splitscheme(as_url(zip_path, 'zip://'))[1]
			with self.assertRaises(OSError) as cm:
				self._fs.mkdir(zip_url_path + '/nonexistent/dir')
			self.assertEqual(ENOENT, cm.exception.errno)
	def test_mkdir_empty(self):
		with TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, 'test.zip')
			self._fs.mkdir(splitscheme(as_url(zip_path))[1])
			with ZipFile(zip_path) as zip_file:
				self.assertEqual([], zip_file.namelist())
	def test_delete_file(self):
		self._test_delete('ZipFileTest/Directory/Subdirectory/file 3.txt')
	def _test_delete(self, path_in_zip):
		expected_contents = self._get_zip_contents()
		self._pop_from_dir_dict(expected_contents, path_in_zip)
		self._fs.delete(self._path(path_in_zip))
		self.assertEqual(expected_contents, self._get_zip_contents())
	def test_delete_directory(self):
		self._test_delete('ZipFileTest/Directory')
	def test_delete_empty_directory(self):
		self._test_delete('ZipFileTest/Empty directory')
	def test_delete_main_directory(self):
		self._test_delete('ZipFileTest')
	def test_delete_nonexistent(self):
		with self.assertRaises(FileNotFoundError):
			self._fs.delete(self._path('nonexistent'))
	def test_move_file_out_of_archive(self):
		file_path = 'ZipFileTest/Directory/Subdirectory/file 3.txt'
		expected_zip_contents = self._get_zip_contents()
		removed = self._pop_from_dir_dict(expected_zip_contents, file_path)
		with TemporaryDirectory() as tmp_dir:
			dst = os.path.join(tmp_dir, 'test.tzt')
			self._fs.move(self._url(file_path), as_url(dst))
			self.assertEqual(expected_zip_contents, self._get_zip_contents())
			with open(dst) as f:
				self.assertEqual(removed, f.read())
	def test_move_dir_out_of_archive(self):
		self._test_move_dir_out_of_archive('ZipFileTest/Directory')
	def test_move_empty_dir_out_of_archive(self):
		self._test_move_dir_out_of_archive('ZipFileTest/Empty directory')
	def test_move_main_dir_out_of_archive(self):
		self._test_move_dir_out_of_archive('ZipFileTest')
	def _test_move_dir_out_of_archive(self, path_in_zip):
		expected_zip_contents = self._get_zip_contents()
		removed = self._pop_from_dir_dict(expected_zip_contents, path_in_zip)
		with TemporaryDirectory() as tmp_dir:
			dst_dir = os.path.join(tmp_dir, 'dest')
			self._fs.move(self._url(path_in_zip), as_url(dst_dir))
			self.assertEqual(expected_zip_contents, self._get_zip_contents())
			self.assertEqual(removed, self._read_directory(dst_dir))
	def test_move_file_into_archive(self):
		expected_zip_contents = self._get_zip_contents()
		with TemporaryDirectory() as tmp_dir:
			file_path = os.path.join(tmp_dir, 'test.txt')
			with open(file_path, 'w') as f:
				f.write('success!')
			dst_url = self._url('test_dest.txt')
			self._fs.move(as_url(file_path), dst_url)
			self.assertFalse(Path(file_path).exists())
			expected_zip_contents['test_dest.txt'] = 'success!'
			self.assertEqual(expected_zip_contents, self._get_zip_contents())
	def test_rename_directory(self):
		expected_contents = self._get_zip_contents()
		file_path = 'ZipFileTest/Directory'
		expected_contents['Destination'] = \
			self._pop_from_dir_dict(expected_contents, file_path)
		self._fs.move(self._url(file_path), self._url('Destination'))
		self.assertEqual(expected_contents, self._get_zip_contents())
	def test_rename_file(self):
		expected_contents = self._get_zip_contents()
		src_path = 'ZipFileTest/Directory/Subdirectory/file 3.txt'
		expected_contents['ZipFileTest']['Directory']['destination.txt'] = \
			self._pop_from_dir_dict(expected_contents, src_path)
		self._fs.move(
			self._url(src_path),
			self._url('ZipFileTest/Directory/destination.txt')
		)
		self.assertEqual(expected_contents, self._get_zip_contents())
	def test_move_file_between_archives(self, operation=None, get_contents=None):
		if operation is None:
			operation = self._fs.move
		if get_contents is None:
			get_contents = self._pop_from_dir_dict
		src_path = 'ZipFileTest/Directory/Subdirectory/file 3.txt'
		expected_contents = self._get_zip_contents()
		src_contents = get_contents(expected_contents, src_path)
		with TemporaryDirectory() as dst_dir:
			dst_zip = os.path.join(dst_dir, 'dest.zip')
			# Give the Zip file some contents:
			dummy_txt = os.path.join(dst_dir, 'dummy.txt')
			dummy_contents = 'some contents'
			with open(dummy_txt, 'w') as f:
				f.write(dummy_contents)
			with ZipFile(dst_zip, 'w') as zip_file:
				zip_file.write(dummy_txt, 'dummy.txt')
			dst_url = join(as_url(dst_zip, 'zip://'), 'dest.txt')
			operation(self._url(src_path), dst_url)
			self.assertEqual(expected_contents, self._get_zip_contents())
			self.assertEqual(
				{'dummy.txt': dummy_contents, 'dest.txt': src_contents},
				self._get_zip_contents(dst_zip)
			)
	def test_copy_file_between_archives(self):
		self.test_move_file_between_archives(
			self._fs.copy, self._get_from_dir_dict
		)
	def test_size_bytes_file(self):
		file_path = 'ZipFileTest/Directory/Subdirectory/file 3.txt'
		file_contents = self._get_zip_contents(path_in_zip=file_path)
		self.assertEqual(
			len(file_contents), self._fs.size_bytes(self._path(file_path))
		)
	def test_size_bytes_dir(self):
		dir_path = self._path('ZipFileTest/Directory/Subdirectory')
		self.assertIn(self._fs.size_bytes(dir_path), (0, None))
	def test_size_bytes_root(self):
		self.assertIsNone(self._fs.size_bytes(self._path('')))
	def test_size_bytes_nonexistent_zip(self):
		with self.assertRaises(FileNotFoundError):
			self._fs.size_bytes('nonexistent')
	def test_size_bytes_nonexistent_path_in_zip(self):
		with self.assertRaises(FileNotFoundError):
			self._fs.size_bytes(self._path('nonexistent'))
	def test_modified_datetime_file(self):
		file_path = 'ZipFileTest/Directory/Subdirectory/file 3.txt'
		mtime = self._fs.modified_datetime(self._path(file_path))
		# Compare by date only because the time depends on the system time zone:
		self.assertEqual(date(2017, 11, 8), mtime.date())
	def test_modified_datetime_dir(self):
		dir_path = self._path('ZipFileTest/Empty directory')
		mtime = self._fs.modified_datetime(dir_path)
		# Compare by date only because the time depends on the system time zone:
		self.assertEqual(date(2017, 11, 8), mtime.date())
	def test_modified_datetime_root(self):
		self.assertIsNone(self._fs.modified_datetime(self._path('')))
	def test_modified_datetime_nonexistent_zip(self):
		with self.assertRaises(FileNotFoundError):
			self._fs.modified_datetime('nonexistent')
	def test_modified_datetime_nonexistent_path_in_zip(self):
		with self.assertRaises(FileNotFoundError):
			self._fs.modified_datetime(self._path('nonexistent'))
	def test_resolve_nonexistent_zip_raises_filenotfounderror(self):
		with self.assertRaises(FileNotFoundError):
			tmp_url = as_url(self._tmp_dir.name)
			self._fs.resolve(splitscheme(join(tmp_url, 'non-existent.zip'))[1])
	def test_resolve_nonexistent_file(self):
		with self.assertRaises(FileNotFoundError):
			self._fs.resolve('non-existent')
	def _expect_iterdir_result(self, path_in_zip, expected_contents):
		full_path = self._path(path_in_zip)
		self.assertEqual(
			set(self._normalize_unicode(s) for s in expected_contents),
			set(self._normalize_unicode(s) for s in self._fs.iterdir(full_path))
		)
	def _normalize_unicode(self, name):
		# Consider ç: It can be encoded in Unicode as "latin small letter c
		# with cedilla" (U+00E7) but also as a c followed by "combining
		# cedilla" (U+0327). This source file uses the former, but on Mac,
		# the file system gives us the latter. To accommodate this, we normalize
		# Unicode file names before comparing them:
		return normalize('NFC', name)
	def _url(self, path_in_zip):
		return as_url(self._path(path_in_zip), 'zip://')
	def _path(self, path_in_zip, zip_path=None):
		if zip_path is None:
			zip_path = self._zip
		return zip_path.replace(os.sep, '/') + \
			   ('/' if path_in_zip else '') + \
			   path_in_zip
	def _get_zip_contents(self, zip_path=None, path_in_zip=None):
		if zip_path is None:
			zip_path = self._zip
		with TemporaryDirectory() as tmp_dir:
			with ZipFile(zip_path) as zip_file:
				zip_file.extractall(tmp_dir)
			zip_contents = self._read_directory(tmp_dir)
			return self._get_from_dir_dict(zip_contents, path_in_zip)
	def _pop_from_dir_dict(self, dir_dict, path):
		parts = path.split('/')
		for part in parts[:-1]:
			dir_dict = dir_dict[part]
		return dir_dict.pop(parts[-1])
	def _get_from_dir_dict(self, dir_dict, path):
		if not path:
			return dir_dict
		for part in path.split('/'):
			dir_dict = dir_dict[part]
		return dir_dict
	def _read_directory(self, dir_path):
		result = {}
		for child in Path(dir_path).iterdir():
			if child.is_dir():
				child_contents = self._read_directory(child)
			else:
				child_contents = child.read_text()
			result[self._normalize_unicode(child.name)] = child_contents
		return result
	def _expect_zip_contents(self, contents, zip_file_path):
		with TemporaryDirectory() as tmp_dir:
			with ZipFile(zip_file_path) as zip_file:
				zip_file.extractall(tmp_dir)
			self.assertEqual(contents, self._read_directory(tmp_dir))
	def _create_empty_zip(self, path):
		ZipFile(path, 'w').close()
	def setUp(self):
		super().setUp()
		archive_password.clear()
		fman_fs = StubFS()
		self._fs = ZipFileSystem(fman_fs, {'.zip'})
		fman_fs.add_child(self._fs)
		self._tmp_dir = TemporaryDirectory()
		self._zip = copyfile(
			os.path.join(os.path.dirname(__file__), 'ZipFileSystemTest.zip'),
			os.path.join(self._tmp_dir.name, 'ZipFileSystemTest.zip')
		)
		self._dirs_in_zip = (
			'', 'ZipFileTest', 'ZipFileTest/Directory',
			'ZipFileTest/Directory/Subdirectory', 'ZipFileTest/Empty directory'
		)
		self._files_in_zip = (
			'ZipFileTest/file.txt', 'ZipFileTest/Directory/file 2.txt',
			'ZipFileTest/Directory/Subdirectory/file 3.txt'
		)
		self.maxDiff = None
	def tearDown(self):
		archive_password.clear()
		self._tmp_dir.cleanup()
		super().tearDown()
