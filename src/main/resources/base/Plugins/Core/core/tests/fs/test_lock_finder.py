import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf

from fman import PLATFORM

from core.fs.local.lock_finder import (
	REASON_OPEN_FILE,
	REASON_WORKING_DIR,
	find_locking_processes,
	list_files,
)


class LockFinderTest(TestCase):
	@skipIf(PLATFORM != 'Windows', 'Restart Manager is Windows-only')
	def test_finds_a_process_with_a_file_open(self):
		with TemporaryDirectory() as directory:
			path = Path(directory, 'open.txt')
			path.write_text('locked')
			with path.open('r'):
				processes = find_locking_processes([directory], [str(path)])

		self.assertIn(
			(os.getpid(), REASON_OPEN_FILE),
			[(process.pid, process.reason) for process in processes],
		)

	@skipIf(PLATFORM != 'Windows', 'Process working directories are Windows-only')
	def test_finds_a_process_whose_working_directory_is_selected(self):
		with TemporaryDirectory() as directory:
			process = subprocess.Popen(
				[sys.executable, '-c', 'import time; time.sleep(30)'],
				cwd=directory,
			)
			try:
				processes = find_locking_processes([directory], [])
			finally:
				process.kill()
				process.wait()

		self.assertIn(
			(process.pid, REASON_WORKING_DIR),
			[(item.pid, item.reason) for item in processes],
		)

	def test_list_files_walks_nested_directories_and_keeps_plain_files(self):
		with TemporaryDirectory() as directory:
			root = Path(directory)
			nested = root / 'nested'
			nested.mkdir()
			first = root / 'first.txt'
			second = nested / 'second.txt'
			first.touch()
			second.touch()

			self.assertCountEqual(
				[str(first), str(second)], list_files([directory, str(first)])
			)
