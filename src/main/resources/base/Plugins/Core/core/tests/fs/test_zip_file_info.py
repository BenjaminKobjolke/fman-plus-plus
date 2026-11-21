from core.fs.zip import ZipFileSystem
from datetime import datetime
from unittest import TestCase


class ZipFileInfoTest(TestCase):
	def setUp(self):
		self.fs = ZipFileSystem(fs=None, suffixes={'.zip'})

	def test_reads_created_and_modified_times(self):
		info = self.fs._read_file_info([
			'Path = file.txt\n',
			'Modified = 2023-12-31 23:59:58.1234567\n',
			'Created = 2024-01-02 03:04:05.1234567\n',
			'\n',
		])
		self.assertEqual(datetime(2024, 1, 2, 3, 4, 5), info.ctime)
		self.assertEqual(datetime(2023, 12, 31, 23, 59, 58), info.mtime)

	def test_empty_created_time_is_none(self):
		info = self.fs._read_file_info([
			'Path = file.txt\n', 'Created = \n', '\n',
		])
		self.assertIsNone(info.ctime)

	def test_missing_created_time_is_none(self):
		info = self.fs._read_file_info(['Path = file.txt\n', '\n'])
		self.assertIsNone(info.ctime)
