"""Tests for parallel and streaming file transfers."""

from core.fileoperations import CopyFiles, MoveFiles
from core.fs.local import LocalFileSystem
from core.tests import StubFS
from core.tests.test_fileoperations import MockProgressDialog
from fman import OK, PLATFORM
from fman.url import as_url, join, splitscheme
from fman.impl.plugins.mother_fs import MotherFileSystem
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Event
from unittest import TestCase
from unittest.mock import patch

import os


class UnavailableDestinationTest(TestCase):
	def test_copy_and_move_report_one_destination_error(self):
		with TemporaryDirectory() as tmp_dir:
			root = Path(tmp_dir)
			blocker = root / 'blocker'
			blocker.write_text('blocker')
			destinations = [(blocker / 'new', False)]
			if PLATFORM == 'Windows':
				free_drive = next((
					letter for letter in 'ZYXWVUTSRQPONMLKJIHGFED'
					if not os.path.exists(letter + ':\\')
				), None)
				if free_drive:
					destinations.append((
						Path(free_drive + ':\\fman-missing\\new'), True
					))
			for operation in (CopyFiles, MoveFiles):
				for dest_dir, missing_drive in destinations:
					with self.subTest(operation=operation.__name__, dest_dir=dest_dir):
						src = root / (operation.__name__ + '.txt')
						src.write_text('source')
						fs = MotherFileSystem(None)
						fs.add_child('file://', LocalFileSystem())
						dialog = MockProgressDialog(self)
						task = operation([as_url(src)], as_url(dest_dir), fs=fs)
						task._dialog = dialog
						with patch.object(
							dialog, 'show_alert', return_value=OK
						) as alert:
							task()
						self.assertEqual(1, alert.call_count)
						message = alert.call_args.args[0]
						self.assertIn(
							'Could not create the destination folder', message
						)
						self.assertIn(str(dest_dir), message)
						self.assertNotIn('FileExistsError', message)
						if missing_drive:
							self.assertIn(
								'the drive or network share is not available', message
							)
						self.assertEqual('source', src.read_text())
						self.assertEqual('blocker', blocker.read_text())

class StreamingTransferTest(TestCase):
	def test_transfer_starts_before_gathering_ends(self):
		with TemporaryDirectory() as tmp_dir:
			root = as_url(tmp_dir)
			src, dest = join(root, 'src'), join(root, 'dest')
			src_dir = join(src, 'dir')
			backend = _IterdirWaitsForCopy(splitscheme(src_dir)[1])
			fs = StubFS(backend)
			fs.makedirs(src_dir)
			for name in ('a.txt', 'b.txt', 'dir/c.txt'):
				fs.touch(join(src, *name.split('/')))
			# An existing destination folder makes the gathering list src_dir:
			fs.makedirs(join(dest, 'dir'))
			files = [join(src, 'a.txt'), join(src, 'b.txt'), src_dir]
			task = CopyFiles(files, dest, fs=fs)
			task._dialog = MockProgressDialog(self)
			task()
			self.assertTrue(
				backend.copy_started_first,
				'Gathering must not block the transfers already found.'
			)
			self.assertEqual({'c.txt'}, set(fs.iterdir(join(dest, 'dir'))))

class ParallelTransferTest(TestCase):

	_NAMES = ['a.txt', 'b.txt', 'c.txt']

	def test_copy_runs_transfers_at_the_same_time(self):
		self._transfer_at_the_same_time(CopyFiles)
	def test_move_runs_transfers_at_the_same_time(self):
		src = self._transfer_at_the_same_time(MoveFiles)
		self.assertEqual(set(), src, 'Moved files must leave the source.')
	def test_emptied_folder_is_deleted_after_earlier_moves(self):
		task = MoveFiles(['file:///a'], 'file:///b')
		self.assertTrue(
			task._postprocess_directory('file:///a').waits_for_earlier_tasks
		)
	def _transfer_at_the_same_time(self, operation):
		with TemporaryDirectory() as tmp_dir:
			root = as_url(tmp_dir)
			src, dest = join(root, 'src'), join(root, 'dest')
			names = self._NAMES
			backend = _TransfersWaitForOthers(len(names))
			fs = _ParallelStubFS(backend, len(names))
			fs.makedirs(src)
			for name in names:
				fs.touch(join(src, name))
			task = operation([join(src, name) for name in names], dest, fs=fs)
			dialog = MockProgressDialog(self)
			task._dialog = dialog
			task()
			self.assertEqual(set(names), set(fs.iterdir(dest)))
			self.assertIsNotNone(dialog.workers, 'Workers must be shown.')
			return set(fs.iterdir(src))

class ConnectionCountTest(TestCase):
	def test_same_server_is_asked_once(self):
		fs = _ConnectionCountFS({'ftp://h': 5})
		self.assertEqual(
			5, CopyFiles(['ftp://h/a'], 'ftp://h/b', fs=fs)._get_connection_count()
		)
		self.assertEqual(1, len(fs.asked))
		self.assertIn(fs.asked[0], ('ftp://h/a', 'ftp://h/b'))
	def test_different_servers_are_summed(self):
		fs = _ConnectionCountFS({'ftp://h': 3, 'ftp://k': 2})
		self.assertEqual(
			5, CopyFiles(['ftp://h/a'], 'ftp://k/b', fs=fs)._get_connection_count()
		)
		self.assertEqual({'ftp://h/a', 'ftp://k/b'}, set(fs.asked))
	def test_local_none_and_ftp_count_returns_ftp_count(self):
		fs = _ConnectionCountFS({'file:///': None, 'ftp://h': 4})
		self.assertEqual(
			4, CopyFiles(['file:///a'], 'ftp://h/b', fs=fs)._get_connection_count()
		)
	def test_all_unknown_counts_return_none(self):
		fs = _ConnectionCountFS({'file:///': None})
		self.assertIsNone(
			CopyFiles(['file:///a'], 'file:///b', fs=fs)._get_connection_count()
		)

class _ConnectionCountFS(StubFS):
	def __init__(self, answers):
		super().__init__()
		self.answers = answers
		self.asked = []
	def get_connection_count(self, url):
		self.asked.append(url)
		return next(
			count for prefix, count in self.answers.items()
			if url.startswith(prefix)
		)

class _ParallelStubFS(StubFS):
	def __init__(self, backend, parallel_transfers):
		super().__init__(backend)
		self._parallel_transfers = parallel_transfers
	def get_parallel_transfers(self, src_url, dst_url):
		return self._parallel_transfers

class _TransfersWaitForOthers(LocalFileSystem):
	"""
	Each copy or move waits until all of them have started, so a sequential
	transfer times out instead of hanging the test run.
	"""
	_TIMEOUT_SECS = 5
	def __init__(self, count):
		super().__init__()
		self._all_started = Barrier(count, timeout=self._TIMEOUT_SECS)
	def copy(self, src_url, dst_url):
		self._all_started.wait()
		super().copy(src_url, dst_url)
	def move(self, src_url, dst_url):
		self._all_started.wait()
		super().move(src_url, dst_url)

class _IterdirWaitsForCopy(LocalFileSystem):
	"""
	Listing `watched_path` waits until a copy has started. Only a transfer that
	runs while the gathering continues can start one; sequential code would
	time out instead of hanging the test run.
	"""
	_TIMEOUT_SECS = 5
	def __init__(self, watched_path):
		super().__init__()
		self._watched_path = watched_path
		self._copy_started = Event()
		self.copy_started_first = None
	def copy(self, src_url, dst_url):
		self._copy_started.set()
		super().copy(src_url, dst_url)
	def iterdir(self, path):
		if path == self._watched_path and self.copy_started_first is None:
			self.copy_started_first = self._copy_started.wait(self._TIMEOUT_SECS)
		return super().iterdir(path)

