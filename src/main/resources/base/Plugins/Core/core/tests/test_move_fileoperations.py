from os.path import exists
from threading import Event
from unittest import TestCase, skipIf
from unittest.mock import patch

from core.fileoperations import MoveFiles
from core.fs.local import LocalFileSystem
from core.tests.test_fileoperations import FileTreeOperationAT
from core.transfer_workers import DONE
from fman import PLATFORM, Task, YES, NO
from fman.impl.overwrite_dialog import OverwriteChoice
from fman.impl.plugins.mother_fs import MotherFileSystem
from fman.url import join


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
		self, answers=(OverwriteChoice.OVERWRITE, OverwriteChoice.OVERWRITE),
		expect_overrides=(True, True),
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
		self._expect_overwrite('test.txt', OverwriteChoice.SKIP)
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
	def test_failure_after_second_move_keeps_other_successes(self):
		first, second, third = self._make_sources()
		self._expect_alert((
			'Moving 3 files: 1 file failed.\n\n'
			'Error moving second.txt (permission denied).\n\nRetry it?',
			YES | NO, YES
		), answer=NO)
		self._run_move_with_error(second)
		self.assertFalse(self._fs.exists(first))
		self.assertTrue(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(second))
		self.assertFalse(self._fs.exists(join(self.dest, 'second.txt')))
		self.assertFalse(self._fs.exists(third))
		self.assertTrue(self._fs.exists(join(self.dest, 'third.txt')))
	def test_abort_on_overwrite_restores_completed_moves(self):
		first, second, third = self._make_sources()
		dest_second = join(self.dest, 'second.txt')
		self._touch(dest_second, 'old destination')
		self._expect_overwrite('second.txt', OverwriteChoice.ABORT)
		self._run_move()
		self.assertTrue(self._fs.exists(first))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(second))
		self._assert_file_contents_equal(dest_second, 'old destination')
		self.assertTrue(self._fs.exists(third))
	def test_cancel_after_one_move_restores_it(self):
		first, second, third = self._make_sources()
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
		first, second, third = self._make_sources()
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
	def test_last_file_error_keeps_completed_moves(self):
		first, second, third = self._make_sources()
		self._expect_alert((
			'Moving 3 files: 1 file failed.\n\n'
			'Error moving third.txt (permission denied).\n\nRetry it?',
			YES | NO, YES
		), NO)
		self._run_move_with_error(third)
		self.assertFalse(self._fs.exists(first))
		self.assertFalse(self._fs.exists(second))
		self.assertTrue(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertTrue(self._fs.exists(join(self.dest, 'second.txt')))
		self.assertTrue(self._fs.exists(third))
	def test_failed_move_does_not_prevent_later_moves(self):
		first, second, third = self._make_sources()
		self._expect_alert((
			'Moving 3 files: 1 file failed.\n\n'
			'Error moving first.txt (permission denied).\n\nRetry it?',
			YES | NO, YES
		), answer=NO)
		self._run_move_with_error(first)
		self.assertTrue(self._fs.exists(first))
		self.assertFalse(self._fs.exists(join(self.dest, 'first.txt')))
		self.assertFalse(self._fs.exists(second))
		self.assertTrue(self._fs.exists(join(self.dest, 'second.txt')))
		self.assertFalse(self._fs.exists(third))
		self.assertTrue(self._fs.exists(join(self.dest, 'third.txt')))
	def test_successful_move_retry_is_recorded_for_rollback(self):
		first, second, third = self._make_sources()
		self._expect_alert((
			'Moving 3 files: 1 file failed.\n\n'
			'Error moving second.txt (permission denied).\n\nRetry it?',
			YES | NO, YES
		), answer=YES)
		backend = self._fs._children['file://']
		rename = backend._rename
		attempts = {second: 0}
		def rename_once_then_succeed(src_url, dst_url):
			if src_url == second:
				attempts[src_url] += 1
				if attempts[src_url] == 1:
					raise OSError(13, 'permission denied')
			rename(src_url, dst_url)
		task = MoveFiles([first, second, third], self.dest, fs=self._fs)
		task._get_worker_count = lambda: 1
		task._dialog = self._progress_dialog
		done = []
		on_task_done = task._on_task_done
		def record_and_track(completed_task):
			done.append(completed_task)
			on_task_done(completed_task)
		task._on_task_done = record_and_track
		with patch.object(backend, '_rename', side_effect=rename_once_then_succeed):
			task()
		self._progress_dialog.verify_expected_dialogs_were_shown()
		self.assertEqual(2, attempts[second])
		self.assertIn(
			'Moving second.txt', [item.get_title() for item in done]
		)
		self.assertTrue(self._fs.exists(join(self.dest, 'second.txt')))
	def test_failed_move_keeps_new_destination_and_completed_files(self):
		first, second, third = self._make_sources()
		new_dest = join(self.dest, 'new-destination')
		self._expect_alert((
			'Moving 3 files: 1 file failed.\n\n'
			'Error moving second.txt (permission denied).\n\nRetry it?',
			YES | NO, YES
		), answer=NO)
		self._run_move_with_error(second, dest_dir=new_dest)
		self.assertTrue(self._fs.exists(new_dest))
		self.assertTrue(self._fs.exists(self.dest))
		self.assertFalse(self._fs.exists(first))
		self.assertTrue(self._fs.exists(second))
		self.assertFalse(self._fs.exists(third))
	def test_failed_move_preserves_preexisting_destination_folder(self):
		first, second, third = self._make_sources()
		foreign_file = join(self.dest, 'foreign.txt')
		self._touch(foreign_file, 'foreign')
		self._expect_alert((
			'Moving 3 files: 1 file failed.\n\n'
			'Error moving second.txt (permission denied).\n\nRetry it?',
			YES | NO, YES
		), answer=NO)
		self._run_move_with_error(second)
		self.assertTrue(self._fs.exists(self.dest))
		self._assert_file_contents_equal(foreign_file, 'foreign')
		self.assertFalse(self._fs.exists(first))
		self.assertFalse(self._fs.exists(third))
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
