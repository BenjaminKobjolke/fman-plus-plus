from core.fileoperations import CopyFiles, MoveFiles
from core.transfer_workers import DONE
from core.fs.local import LocalFileSystem
from core.tests import StubFS
from fman import YES, NO, OK, YES_TO_ALL, NO_TO_ALL, ABORT, PLATFORM, Task
from fman.url import join, dirname, as_url, as_human_readable
from os.path import exists
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase, skipIf
from unittest.mock import patch
from fman.impl.plugins.mother_fs import MotherFileSystem

import os
import os.path
import stat

class FileTreeOperationAT:
	def test_core_file_operations_are_minimizable(self):
		self.assertTrue(self.operation.minimizable)

	if PLATFORM == 'Windows':
		_NO_SUCH_FILE_MSG = 'the system cannot find the file specified'
	else:
		_NO_SUCH_FILE_MSG = 'no such file or directory'

	def __init__(self, operation, operation_descr_verb, methodName='runTest'):
		super().__init__(methodName=methodName)
		self.operation = operation
		self.operation_descr_verb = operation_descr_verb
	def test_single_file(self, dest_dir=None):
		if dest_dir is None:
			dest_dir = self.dest
		src_file = join(self.src, 'test.txt')
		self._touch(src_file, '1234')
		self._perform_on(src_file, dest_dir=dest_dir)
		self._expect_files({'test.txt'}, dest_dir)
		self._assert_file_contents_equal(join(dest_dir, 'test.txt'), '1234')
		return src_file
	def test_singe_file_dest_dir_does_not_exist(self):
		self.test_single_file(dest_dir=join(self.dest, 'subdir'))
	def test_empty_directory(self):
		empty_dir = join(self.src, 'test')
		self._mkdir(empty_dir)
		self._perform_on(empty_dir)
		self._expect_files({'test'})
		self._expect_files(set(), in_dir=join(self.dest, 'test'))
		return empty_dir
	def test_directory_several_files(self, dest_dir=None):
		if dest_dir is None:
			dest_dir = self.dest
		file_outside_dir = join(self.src, 'file1.txt')
		self._touch(file_outside_dir)
		dir_ = join(self.src, 'dir')
		self._mkdir(dir_)
		file_in_dir = join(dir_, 'file.txt')
		self._touch(file_in_dir)
		executable_in_dir = join(dir_, 'executable')
		self._touch(executable_in_dir, 'abc')
		if PLATFORM != 'Windows':
			st_mode = self._stat(executable_in_dir).st_mode
			self._chmod(executable_in_dir, st_mode | stat.S_IEXEC)
		self._perform_on(file_outside_dir, dir_, dest_dir=dest_dir)
		self._expect_files({'file1.txt', 'dir'}, dest_dir)
		self._expect_files({'executable', 'file.txt'}, join(dest_dir, 'dir'))
		executable_dst = join(dest_dir, 'dir', 'executable')
		self._assert_file_contents_equal(executable_dst, 'abc')
		if PLATFORM != 'Windows':
			self.assertTrue(self._stat(executable_dst).st_mode & stat.S_IEXEC)
		return [file_outside_dir, dir_]
	def test_directory_several_files_dest_dir_does_not_exist(self):
		self.test_directory_several_files(dest_dir=join(self.dest, 'subdir'))
	def test_overwrite_files(
		self, answers=(YES, YES), expect_overrides=(True, True),
		files=('a.txt', 'b.txt'), perform_on_files=None
	):
		if perform_on_files is None:
			perform_on_files = files
		src_files = [join(self.src, *relpath.split('/')) for relpath in files]
		dest_files = [join(self.dest, *relpath.split('/')) for relpath in files]
		file_contents = lambda src_file_path: os.path.basename(src_file_path)
		for i, src_file_path in enumerate(src_files):
			self._makedirs(dirname(src_file_path), exist_ok=True)
			self._touch(src_file_path, file_contents(src_file_path))
			dest_file_path = dest_files[i]
			self._makedirs(dirname(dest_file_path), exist_ok=True)
			self._touch(dest_file_path)
		for i, answer in enumerate(answers):
			file_name = os.path.basename(files[i])
			self._expect_alert(
				('%s exists. Do you want to overwrite it?' % file_name,
				 YES | NO | YES_TO_ALL | NO_TO_ALL | ABORT, YES),
				answer=answer
			)
		self._perform_on(*[join(self.src, fname) for fname in perform_on_files])
		for i, expect_override in enumerate(expect_overrides):
			dest_file = dest_files[i]
			with self._open(dest_file, 'r') as f:
				contents = f.read()
			if expect_override:
				self.assertEqual(file_contents(src_files[i]), contents)
			else:
				self.assertEqual(
					'', contents,
					'File %s was overwritten, contrary to expectations.' %
					os.path.basename(dest_file)
				)
		return src_files
	def test_overwrite_files_no_yes(self):
		self.test_overwrite_files((NO, YES), (False, True))
	def test_overwrite_files_yes_all(self):
		self.test_overwrite_files((YES_TO_ALL,), (True, True))
	def test_overwrite_files_no_all(self):
		self.test_overwrite_files((NO_TO_ALL,), (False, False))
	def test_overwrite_files_yes_no_all(self):
		self.test_overwrite_files((YES, NO_TO_ALL), (True, False))
	def test_overwrite_files_abort(self):
		self.test_overwrite_files((ABORT,), (False, False))
	def test_overwrite_files_in_directory(self):
		self.test_overwrite_files(
			files=('dir/a.txt', 'b.txt'), perform_on_files=('dir', 'b.txt')
		)
	def test_overwrite_directory_abort(self):
		self.test_overwrite_files(
			(ABORT,), (False, False,), files=('dir/a/a.txt', 'dir/b/b.txt'),
			perform_on_files=('dir',)
		)
	def test_move_to_self(self):
		a, b = join(self.dest, 'a'), join(self.dest, 'b')
		c = join(self.external_dir, 'c')
		dir_ = join(self.dest, 'dir')
		self._makedirs(dir_)
		files = [a, b, c]
		for file_ in files:
			self._touch(file_)
		# Expect alert only once:
		self._expect_alert(
			('You cannot %s a file to itself.' % self.operation_descr_verb,),
			answer=OK
		)
		self._perform_on(dir_, *files)
	def test_move_dir_to_self(self):
		dir_ = join(self.src, 'dir')
		self._makedirs(dir_)
		self._expect_alert(
			('You cannot %s a file to itself.' % self.operation_descr_verb,),
			answer=OK
		)
		self._perform_on(dir_, dest_dir=self.src)
	def test_move_to_own_subdir(self):
		dir_ = join(self.src, 'dir')
		subdir = join(dir_, 'subdir')
		self._makedirs(subdir)
		self._expect_alert(
			('You cannot %s a file to itself.' % self.operation_descr_verb,),
			answer=OK
		)
		self._perform_on(dir_, dest_dir=subdir)
	def test_move_to_own_nonexistent_subdir(self):
		dir_ = join(self.src, 'dir')
		self._touch(join(dir_, 'file.txt'))
		self._expect_alert(
			('You cannot %s a file to itself.' % self.operation_descr_verb,),
			answer=OK
		)
		self._perform_on(dir_, dest_dir=join(dir_, 'subdir'))
		# The rejected transfer must not have created its destination:
		self._expect_files({'file.txt'}, in_dir=dir_)
	def test_external_file(self):
		external_file = join(self.external_dir, 'test.txt')
		self._touch(external_file)
		self._perform_on(external_file)
		self._expect_files({'test.txt'})
		return external_file
	def test_nested_dir(self):
		parent_dir = join(self.src, 'parent_dir')
		nested_dir = join(parent_dir, 'nested_dir')
		text_file = join(nested_dir, 'file.txt')
		self._makedirs(nested_dir)
		self._touch(text_file)
		self._perform_on(parent_dir)
		self._expect_files({'parent_dir'})
		self._expect_files({'nested_dir'}, join(self.dest, 'parent_dir'))
		self._expect_files(
			{'file.txt'}, join(self.dest, 'parent_dir', 'nested_dir')
		)
		return parent_dir
	def test_symlink(self):
		symlink_source = join(self.src, 'symlink_source')
		self._touch(symlink_source)
		symlink = join(self.src, 'symlink')
		self._symlink(symlink_source, symlink)
		self._perform_on(symlink)
		self._expect_files({'symlink'})
		symlink_dest = join(self.dest, 'symlink')
		self.assertTrue(self._islink(symlink_dest))
		symlink_dest_source = self._readlink(symlink_dest)
		self.assertTrue(self._fs.samefile(symlink_source, symlink_dest_source))
		return symlink
	def test_dest_name(self, src_equals_dest=False, preserves_files=True):
		src_dir = self.dest if src_equals_dest else self.src
		foo = join(src_dir, 'foo')
		self._touch(foo, '1234')
		self._perform_on(foo, dest_name='bar')
		expected_files = {'bar'}
		if preserves_files and src_equals_dest:
			expected_files.add('foo')
		self._expect_files(expected_files)
		self._assert_file_contents_equal(join(self.dest, 'bar'), '1234')
		return foo
	def test_dest_name_same_dir(self):
		self.test_dest_name(src_equals_dest=True)
	def test_error(self, answer_1=YES, answer_2=YES):
		nonexistent_file_1 = join(self.src, 'foo1.txt')
		nonexistent_file_2 = join(self.src, 'foo2.txt')
		existent_file = join(self.src, 'bar.txt')
		self._touch(existent_file)
		self._expect_alert(
			('Could not %s %s (%s). '
			 'Do you want to continue?' % (
				self.operation_descr_verb,
				as_human_readable(nonexistent_file_1), self._NO_SUCH_FILE_MSG
			 ),
			 YES | YES_TO_ALL | ABORT, YES),
			answer=answer_1
		)
		if not answer_1 & ABORT and not answer_1 & YES_TO_ALL:
			self._expect_alert(
				('Could not %s %s (%s). '
				 'Do you want to continue?' % (
					 self.operation_descr_verb,
					 as_human_readable(nonexistent_file_2),
					 self._NO_SUCH_FILE_MSG
				 ),
				 YES | YES_TO_ALL | ABORT, YES),
				answer=answer_2
			)
		self._perform_on(nonexistent_file_1, nonexistent_file_2, existent_file)
		if not answer_1 & ABORT and not answer_2 & ABORT:
			expected_files = {'bar.txt'}
		else:
			expected_files = set()
		self._expect_files(expected_files)
	def test_error_yes_to_all(self):
		self.test_error(answer_1=YES_TO_ALL)
	def test_error_abort(self):
		self.test_error(answer_1=ABORT)
	def test_error_only_one_file(self):
		nonexistent_file = join(self.src, 'foo.txt')
		file_path = as_human_readable(nonexistent_file)
		message = 'Could not %s %s (%s).' % \
		          (self.operation_descr_verb, file_path, self._NO_SUCH_FILE_MSG)
		self._expect_alert((message, OK, OK), answer=OK)
		self._perform_on(nonexistent_file)
	def test_relative_path_parent_dir(self):
		src_file = join(self.src, 'test.txt')
		self._touch(src_file, '1234')
		self._perform_on(src_file, dest_dir='..')
		dest_dir_abs = dirname(self.src)
		self._expect_files({'src', 'test.txt'}, dest_dir_abs)
		self._assert_file_contents_equal(join(dest_dir_abs, 'test.txt'), '1234')
	def test_relative_path_subdir(self):
		src_file = join(self.src, 'test.txt')
		self._touch(src_file, '1234')
		subdir = join(self.src, 'subdir')
		self._makedirs(subdir, exist_ok=True)
		self._perform_on(src_file, dest_dir='subdir')
		self._expect_files({'test.txt'}, subdir)
		self._assert_file_contents_equal(join(subdir, 'test.txt'), '1234')
	def test_drag_and_drop_file(self):
		src_file = join(self.src, 'test.txt')
		self._touch(src_file, '1234')
		self._perform_on(src_file)
		self._expect_files({'test.txt'})
		self._assert_file_contents_equal(join(self.dest, 'test.txt'), '1234')
	def test_copy_paste_directory(self):
		self._touch(join(self.src, 'dir', 'test.txt'))
		self._makedirs(join(self.dest, 'dir'))
		self._perform_on(join(self.src, 'dir'))
		self._expect_files({'test.txt'}, in_dir=join(self.dest, 'dir'))
	def test_overwrite_directory_file_in_subdir(self):
		self._touch(join(self.src, 'dir1', 'dir2', 'test.txt'))
		self._makedirs(join(self.dest, 'dir1', 'dir2'))
		self._perform_on(join(self.src, 'dir1'))
		self._expect_files({'test.txt'}, in_dir=join(self.dest, 'dir1', 'dir2'))
	def setUp(self):
		super().setUp()
		self._fs = StubFS()
		self._progress_dialog = MockProgressDialog(self)
		self._tmp_dir = TemporaryDirectory()
		self._root = as_url(self._tmp_dir.name)
		# We need intermediate 'src-parent' for test_relative_path_parent_dir:
		self.src = join(self._root, 'src-parent', 'src')
		self._makedirs(self.src)
		self.dest = join(self._root, 'dest')
		self._makedirs(self.dest)
		self.external_dir = join(self._root, 'external-dir')
		self._makedirs(self.external_dir)
		# Create a dummy file to test that not _all_ files are copied from src:
		self._touch(join(self.src, 'dummy'))
	def tearDown(self):
		self._tmp_dir.cleanup()
		super().tearDown()
	def _perform_on(self, *files, dest_dir=None, dest_name=None):
		if dest_dir is None:
			dest_dir = self.dest
		op = self.operation(files, dest_dir, dest_name, self._fs)
		op._dialog = self._progress_dialog
		op()
		self._progress_dialog.verify_expected_dialogs_were_shown()
	def _assert_file_contents_equal(self, url, expected_contents):
		with self._open(url, 'r') as f:
			self.assertEqual(expected_contents, f.read())
	def _touch(self, file_url, contents=None):
		self._makedirs(dirname(file_url), exist_ok=True)
		self._fs.touch(file_url)
		if contents is not None:
			with self._open(file_url, 'w') as f:
				f.write(contents)
	def _mkdir(self, dir_url):
		self._fs.mkdir(dir_url)
	def _makedirs(self, dir_url, exist_ok=False):
		self._fs.makedirs(dir_url, exist_ok=exist_ok)
	def _open(self, file_url, mode):
		return open(as_human_readable(file_url), mode)
	def _stat(self, file_url):
		return os.stat(as_human_readable(file_url))
	def _chmod(self, file_url, mode):
		return os.chmod(as_human_readable(file_url), mode)
	def _symlink(self, src_url, dst_url):
		os.symlink(as_human_readable(src_url), as_human_readable(dst_url))
	def _islink(self, file_url):
		return os.path.islink(as_human_readable(file_url))
	def _readlink(self, link_url):
		return as_url(os.readlink(as_human_readable(link_url)))
	def _expect_alert(self, args, answer):
		self._progress_dialog.expect_alert(args, answer)
	def _expect_files(self, files, in_dir=None):
		if in_dir is None:
			in_dir = self.dest
		self.assertEqual(files, set(self._fs.iterdir(in_dir)))

try:
	from os import geteuid
except ImportError:
	_is_root = False
else:
	_is_root = geteuid() == 0

class CopyFilesTest(FileTreeOperationAT, TestCase):
	def __init__(self, methodName='runTest'):
		super().__init__(CopyFiles, 'copy', methodName)
	@skipIf(_is_root, 'Skip this test when run by root')
	def test_overwrite_locked_file(self):
		# Would also like to have this as a test case in MoveFilesTest but the
		# call to chmod(0o444) which we use to lock the file doesn't prevent the
		# file from being overwritten by a move. Another solution would be to
		# chown the file as a different user, but then the test would require
		# root privileges. So keep it here only for now.
		dir_ = join(self.src, 'dir')
		self._fs.makedirs(dir_)
		src_file = join(dir_, 'foo.txt')
		self._touch(src_file, 'dstn')
		dest_dir = join(self.dest, 'dir')
		self._fs.makedirs(dest_dir)
		locked_dest_file = join(dest_dir, 'foo.txt')
		self._touch(locked_dest_file)
		self._chmod(locked_dest_file, 0o444)
		try:
			self._expect_alert(
				('foo.txt exists. Do you want to overwrite it?',
				 YES | NO | YES_TO_ALL | NO_TO_ALL | ABORT, YES), answer=YES
			)
			self._expect_alert(
				('Error copying foo.txt (%s).' % (
					'access is denied' if PLATFORM == 'Windows'
					else 'permission denied'
				), OK, OK),
				answer=OK
			)
			self._perform_on(dir_)
		finally:
			# Make the file writeable again because on Windows, the temp dir
			# containing it can't be cleaned up otherwise.
			self._chmod(locked_dest_file, 0o777)
	def test_abort_does_not_roll_back_successful_copies(self):
		first, second, third = self._make_copy_sources()
		self._expect_alert(
			('Error copying second.txt (permission denied). Do you want to continue?',
			 YES | YES_TO_ALL | ABORT, YES), answer=ABORT
		)
		backend = next(iter(self._fs._backends.values()))
		copy = backend.copy
		def copy_or_fail(src_url, dst_url):
			if src_url == second:
				raise OSError(13, 'permission denied')
			copy(src_url, dst_url)
		with patch.object(backend, 'copy', side_effect=copy_or_fail):
			task = CopyFiles([first, second, third], self.dest, fs=self._fs)
			task._dialog = self._progress_dialog
			task()
		self._progress_dialog.verify_expected_dialogs_were_shown()
		self.assertTrue(self._fs.exists(first))
		self.assertTrue(self._fs.exists(second))
		self.assertTrue(self._fs.exists(third))
		self.assertTrue(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertFalse(self._fs.exists(join(self.dest, 'second.txt')))
		self.assertFalse(self._fs.exists(join(self.dest, 'third.txt')))
	def test_reports_file_and_directory_after_they_are_copied(self):
		file_url = join(self.src, 'file.txt')
		dir_url = join(self.src, 'dir')
		self._touch(file_url)
		self._touch(join(dir_url, 'inside.txt'))
		reported = []
		task = CopyFiles([file_url, dir_url], self.dest, fs=self._fs,
					 on_file_done=reported.append)
		task._dialog = self._progress_dialog

		task()

		self.assertCountEqual([file_url, dir_url], reported)
	def test_reports_only_completed_items_after_abort(self):
		first, second, third = self._make_copy_sources()
		self._expect_alert(
			('Error copying second.txt (permission denied). Do you want to continue?',
			 YES | YES_TO_ALL | ABORT, YES), answer=ABORT
		)
		backend = next(iter(self._fs._backends.values()))
		copy = backend.copy
		def copy_or_fail(src_url, dst_url):
			if src_url == second:
				raise OSError(13, 'permission denied')
			copy(src_url, dst_url)
		reported = []
		with patch.object(backend, 'copy', side_effect=copy_or_fail):
			task = CopyFiles([first, second, third], self.dest, fs=self._fs,
						 on_file_done=reported.append)
			task._dialog = self._progress_dialog
			task()
		self._progress_dialog.verify_expected_dialogs_were_shown()
		self.assertEqual([first], reported)
	def test_error_continued_reports_later_items_but_not_failed_item(self):
		first, second, third = self._make_copy_sources()
		self._expect_alert(
			('Error copying second.txt (permission denied). Do you want to continue?',
			 YES | YES_TO_ALL | ABORT, YES), answer=YES
		)
		backend = next(iter(self._fs._backends.values()))
		copy = backend.copy
		def copy_or_fail(src_url, dst_url):
			if src_url == second:
				raise OSError(13, 'permission denied')
			copy(src_url, dst_url)
		reported = []
		with patch.object(backend, 'copy', side_effect=copy_or_fail):
			task = CopyFiles([first, second, third], self.dest, fs=self._fs,
						 on_file_done=reported.append)
			task._dialog = self._progress_dialog
			task()
		self._progress_dialog.verify_expected_dialogs_were_shown()
		self.assertCountEqual([first, third], reported)
	def test_overwrite_no_reports_only_the_other_item(self):
		first, second, _ = self._make_copy_sources()
		self._touch(join(self.dest, 'second.txt'))
		self._expect_alert(
			('second.txt exists. Do you want to overwrite it?',
			 YES | NO | YES_TO_ALL | NO_TO_ALL | ABORT, YES), answer=NO
		)
		reported = []
		task = CopyFiles([first, second], self.dest, fs=self._fs,
					 on_file_done=reported.append)
		task._dialog = self._progress_dialog
		task()
		self._progress_dialog.verify_expected_dialogs_were_shown()
		self.assertEqual([first], reported)
	def test_merged_folder_with_skipped_file_is_not_reported(self):
		src_dir = join(self.src, 'dir')
		dest_dir = join(self.dest, 'dir')
		src_file = join(src_dir, 'inside.txt')
		self._touch(src_file)
		self._touch(join(dest_dir, 'inside.txt'))
		self._expect_alert(
			('inside.txt exists. Do you want to overwrite it?',
			 YES | NO | YES_TO_ALL | NO_TO_ALL | ABORT, YES), answer=NO
		)
		reported = []
		task = CopyFiles([src_dir], self.dest, fs=self._fs,
					 on_file_done=reported.append)
		task._dialog = self._progress_dialog
		task()
		self._progress_dialog.verify_expected_dialogs_were_shown()
		self.assertEqual([], reported)
	def _make_copy_sources(self):
		files = [join(self.src, name + '.txt') for name in ('first', 'second', 'third')]
		for name, file_url in zip(('first', 'second', 'third'), files):
			self._touch(file_url, name)
		return files

class MoveFilesTest(FileTreeOperationAT, TestCase):
	def __init__(self, methodName='runTest'):
		super().__init__(MoveFiles, 'move', methodName)
	def setUp(self):
		super().setUp()
		self._fs = MotherFileSystem(None)
		local_fs = LocalFileSystem()
		self._fs.add_child(local_fs.scheme, local_fs)
	def test_single_file(self, dest_dir=None):
		src_file = super().test_single_file(dest_dir)
		self.assertFalse(exists(src_file))
	def test_empty_directory(self):
		empty_dir_src = super().test_empty_directory()
		self.assertFalse(exists(empty_dir_src))
	def test_directory_several_files(self, dest_dir=None):
		src_files = super().test_directory_several_files(dest_dir=dest_dir)
		for file_ in src_files:
			self.assertFalse(exists(file_))
	def test_overwrite_files(
		self, answers=(YES, YES), expect_overrides=(True, True),
		files=('a.txt', 'b.txt'), perform_on_files=None
	):
		src_files = super().test_overwrite_files(
			answers, expect_overrides, files, perform_on_files
		)
		for i, file_ in enumerate(src_files):
			if expect_overrides[i]:
				self.assertFalse(exists(file_), file_)
	@skipIf(PLATFORM == 'Linux', 'Case-insensitive file systems only')
	def test_rename_directory_case(self):
		container = join(self.dest, 'container')
		directory = join(container, 'a')
		self._makedirs(directory)
		self._perform_on(directory, dest_dir=container, dest_name='A')
		self._expect_files({'A'}, in_dir=container)
	def test_external_file(self):
		external_file = super().test_external_file()
		self.assertFalse(exists(external_file))
	def test_nested_dir(self):
		parent_dir = super().test_nested_dir()
		self.assertFalse(exists(parent_dir))
	def test_symlink(self):
		symlink = super().test_symlink()
		self.assertFalse(exists(symlink))
	def test_dest_name(self, src_equals_dest=False):
		super().test_dest_name(src_equals_dest, preserves_files=False)
	def test_overwrite_dir_skip_file(self):
		src_dir = join(self.src, 'dir')
		self._makedirs(src_dir)
		src_file = join(src_dir, 'test.txt')
		self._touch(src_file, 'src contents')
		dest_dir = join(self.dest, 'dir')
		self._makedirs(dest_dir)
		dest_file = join(dest_dir, 'test.txt')
		self._touch(dest_file, 'dest contents')
		self._expect_alert(
			('test.txt exists. Do you want to overwrite it?',
			 YES | NO | YES_TO_ALL | NO_TO_ALL | ABORT, YES),
			answer=NO
		)
		self._perform_on(src_dir)
		self.assertTrue(
			self._fs.exists(src_file),
			"Source file was skipped and should not have been deleted."
		)
		self._assert_file_contents_equal(src_file, 'src contents')
		self._assert_file_contents_equal(dest_file, 'dest contents')
	def test_drag_and_drop_file(self):
		super().test_drag_and_drop_file()
		self.assertNotIn('test.txt', self._fs.iterdir(self.src))
	def test_overwrite_directory_file_in_subdir(self):
		super().test_overwrite_directory_file_in_subdir()
		self.assertNotIn('dir1', self._fs.iterdir(self.src))
	def test_abort_after_second_move_error_restores_first(self):
		first, second, third = self._make_move_sources()
		self._expect_alert(
			('Error moving second.txt (permission denied). Do you want to continue?',
			 YES | YES_TO_ALL | ABORT, YES), answer=ABORT
		)
		self._run_move_with_error(second)
		self.assertTrue(self._fs.exists(first))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(second))
		self.assertFalse(self._fs.exists(join(self.dest, 'second.txt')))
		self.assertTrue(self._fs.exists(third))
	def test_abort_on_overwrite_restores_completed_moves(self):
		first, second, third = self._make_move_sources()
		dest_second = join(self.dest, 'second.txt')
		self._touch(dest_second, 'old destination')
		self._expect_alert(
			('second.txt exists. Do you want to overwrite it?',
			 YES | NO | YES_TO_ALL | NO_TO_ALL | ABORT, YES), answer=ABORT
		)
		self._run_move()
		self.assertTrue(self._fs.exists(first))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(second))
		self._assert_file_contents_equal(dest_second, 'old destination')
		self.assertTrue(self._fs.exists(third))
	def test_cancel_after_one_move_restores_it(self):
		first, second, third = self._make_move_sources()
		backend = self._fs._children['file://']
		rename = backend._rename
		def rename_then_cancel(src_url, dst_url):
			rename(src_url, dst_url)
			if src_url == first:
				self._progress_dialog.canceled = True
		with patch.object(backend, '_rename', side_effect=rename_then_cancel):
			with self.assertRaises(Task.Canceled):
				self._run_move()
		self.assertTrue(self._fs.exists(first))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(second))
		self.assertFalse(self._fs.exists(join(self.dest, 'second.txt')))
		self.assertTrue(self._fs.exists(third))
	def test_cancel_during_gathering_restores_completed_move(self):
		first, second, third = self._make_move_sources()
		completed = Event()
		task = MoveFiles([first, second, third], self.dest, fs=self._fs)
		task._dialog = self._progress_dialog
		on_task_done = task._on_task_done
		enqueue = task._enqueue
		def record_completion(completed_task):
			on_task_done(completed_task)
			completed.set()
		task._on_task_done = record_completion
		task._get_worker_count = lambda: 1
		def enqueue_then_cancel(tasks):
			enqueue(tasks)
			task._queue.put(DONE)
			self.assertTrue(completed.wait(5), 'First move did not complete.')
			self._progress_dialog.canceled = True
		task._enqueue = enqueue_then_cancel
		task()
		self.assertTrue(self._fs.exists(first))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(second))
		self.assertTrue(self._fs.exists(third))
	def test_last_file_error_with_ok_restores_completed_moves(self):
		first, second, third = self._make_move_sources()
		self._expect_alert(('Error moving third.txt (permission denied).', OK, OK), OK)
		self._run_move_with_error(third)
		self.assertTrue(self._fs.exists(first))
		self.assertTrue(self._fs.exists(second))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(third))
	def test_continue_after_error_keeps_successful_move(self):
		first, second, third = self._make_move_sources()
		self._expect_alert(
			('Error moving first.txt (permission denied). Do you want to continue?',
			 YES | YES_TO_ALL | ABORT, YES), answer=YES
		)
		self._run_move_with_error(first)
		self.assertTrue(self._fs.exists(first))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertFalse(self._fs.exists(second))
		self.assertTrue(self._fs.exists(join(self.dest, 'second.txt')))
		self.assertFalse(self._fs.exists(third))
		self.assertTrue(self._fs.exists(join(self.dest, 'third.txt')))
	def test_abort_removes_new_destination_folder(self):
		first, second, third = self._make_move_sources()
		new_dest = join(self.dest, 'new-destination')
		self._expect_alert(
			('Error moving second.txt (permission denied). Do you want to continue?',
			 YES | YES_TO_ALL | ABORT, YES), answer=ABORT
		)
		self._run_move_with_error(second, dest_dir=new_dest)
		self.assertFalse(self._fs.exists(new_dest))
		self.assertTrue(self._fs.exists(self.dest))
		self.assertTrue(self._fs.exists(first))
		self.assertTrue(self._fs.exists(second))
		self.assertTrue(self._fs.exists(third))
	def test_abort_preserves_preexisting_destination_folder(self):
		first, second, third = self._make_move_sources()
		foreign_file = join(self.dest, 'foreign.txt')
		self._touch(foreign_file, 'foreign')
		self._expect_alert(
			('Error moving second.txt (permission denied). Do you want to continue?',
			 YES | YES_TO_ALL | ABORT, YES), answer=ABORT
		)
		self._run_move_with_error(second)
		self.assertTrue(self._fs.exists(self.dest))
		self._assert_file_contents_equal(foreign_file, 'foreign')
		self.assertTrue(self._fs.exists(first))
		self.assertTrue(self._fs.exists(third))
	def _make_move_sources(self):
		files = [join(self.src, name + '.txt') for name in ('first', 'second', 'third')]
		for name, file_url in zip(('first', 'second', 'third'), files):
			self._touch(file_url, name)
		return files
	def _run_move(self, dest_dir=None):
		if dest_dir is None:
			dest_dir = self.dest
		self._perform_on(*(join(self.src, name + '.txt')
						for name in ('first', 'second', 'third')),
					 dest_dir=dest_dir)
	def _run_move_with_error(self, failed_src, dest_dir=None):
		backend = self._fs._children['file://']
		rename = backend._rename
		def rename_or_fail(src_url, dst_url):
			if src_url == failed_src:
				raise OSError(13, 'permission denied')
			rename(src_url, dst_url)
		with patch.object(backend, '_rename', side_effect=rename_or_fail):
			self._run_move(dest_dir)

class MockProgressDialog:
	def __init__(self, test_case):
		self._test_case = test_case
		self._progress = 0
		self._expected_alerts = []
		self.workers = None
		self.canceled = False
	def expect_alert(self, args, answer):
		self._expected_alerts.append((args, answer))
	def verify_expected_dialogs_were_shown(self):
		self._test_case.assertEqual(
			[], self._expected_alerts, 'Did not receive all expected alerts.'
		)
	def show_alert(self, *args, **_):
		if not self._expected_alerts:
			self._test_case.fail('Unexpected alert: %r' % args[0])
			return
		expected_args, answer = self._expected_alerts.pop(0)
		self._test_case.assertEqual(expected_args, args, "Wrong alert")
		return answer
	def set_text(self, text):
		pass
	def was_canceled(self):
		return self.canceled
	def set_task_size(self, size):
		pass
	def get_progress(self):
		return self._progress
	def set_progress(self, progress):
		self._progress = progress
	def show_workers(self, workers):
		self.workers = workers
