from datetime import datetime, timezone
from os.path import exists, join
import os
from tempfile import TemporaryDirectory, NamedTemporaryFile
from unittest import TestCase, skipUnless
from unittest.mock import patch

from core.trash import move_to_trash
from core.recycle_bin import (
	RecycleBinEntry, find_entry, parse_entry, restore_entry,
)
from fman import PLATFORM


def _filetime(value):
	return int((value.timestamp() + 11644473600) * 10_000_000)


def _metadata(version, original_path, deleted_at):
	path = original_path.encode('utf-16-le') + b'\0\0'
	if version == 1:
		return (
			(1).to_bytes(8, 'little', signed=True)
			+ (3).to_bytes(8, 'little', signed=True)
			+ _filetime(deleted_at).to_bytes(8, 'little', signed=True)
			+ path.ljust(520, b'\0')
		)
	return (
		(2).to_bytes(8, 'little', signed=True)
		+ (3).to_bytes(8, 'little', signed=True)
		+ _filetime(deleted_at).to_bytes(8, 'little', signed=True)
		+ (len(path) // 2).to_bytes(4, 'little', signed=True)
		+ path
	)


class RecycleBinEntryTest(TestCase):
	def test_parses_version_1_metadata(self):
		with TemporaryDirectory() as folder:
			entry = self._write_and_parse(folder, 1, r'C:\source\a.txt')
		self.assertEqual(r'C:\source\a.txt', entry.original_path)
		self.assertEqual('$Rabc.txt', entry.data_path.rsplit('\\', 1)[-1])
		self.assertEqual('$Iabc.txt', entry.info_path.rsplit('\\', 1)[-1])
		self.assertEqual(3, entry.size)

	def test_parses_version_2_metadata(self):
		with TemporaryDirectory() as folder:
			entry = self._write_and_parse(folder, 2, r'C:\source\b.txt')
		self.assertEqual(r'C:\source\b.txt', entry.original_path)
		self.assertEqual(datetime(2024, 1, 2, tzinfo=timezone.utc), entry.deleted_at)

	def test_rejects_unknown_version(self):
		with TemporaryDirectory() as folder:
			path = join(folder, '$Ix')
			with open(path, 'wb') as file:
				file.write((3).to_bytes(8, 'little') + b'\0' * 32)
			with self.assertRaisesRegex(ValueError, 'version'):
				parse_entry(path)

	def test_rejects_truncated_metadata(self):
		with TemporaryDirectory() as folder:
			path = join(folder, '$Ix')
			with open(path, 'wb') as file:
				file.write(b'\0' * 20)
			with self.assertRaisesRegex(ValueError, '[Tt]runcated'):
				parse_entry(path)

	def _write_and_parse(self, folder, version, original_path):
		path = join(folder, '$Iabc.txt')
		deleted_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
		with open(path, 'wb') as file:
			file.write(_metadata(version, original_path, deleted_at))
		return parse_entry(path)


class FindEntryTest(TestCase):
	def test_accepts_file_url_and_looks_up_native_path(self):
		with TemporaryDirectory() as folder:
			entry = self._entry(folder, '$Inew', r'C:\Users\A.txt', 2)
			with patch(
				'core.recycle_bin.get_current_user_sid',
				return_value='S-1-5-21-test'
			), \
				patch(
					'core.recycle_bin._recycle_bin_directory',
					return_value=folder
				) as directory:
				found = find_entry('file://C:/Users/A.txt')
		self.assertEqual(entry.info_path, found.info_path)
		directory.assert_called_once_with(r'C:\Users\A.txt', 'S-1-5-21-test')

	def test_returns_newest_case_insensitive_original_path_match(self):
		with TemporaryDirectory() as folder:
			old = self._entry(folder, '$Iold', r'C:\Users\A.txt', 1)
			new = self._entry(folder, '$Inew', r'c:\users\a.TXT', 2)
			with patch(
				'core.recycle_bin.get_current_user_sid',
				return_value='S-1-5-21-test'
			), \
				patch(
					'core.recycle_bin._recycle_bin_directory',
					return_value=folder
				):
				found = find_entry(r'C:\USERS\A.txt')
		self.assertEqual(new.info_path, found.info_path)
		self.assertNotEqual(old.info_path, found.info_path)

	def test_returns_none_when_no_path_matches(self):
		with TemporaryDirectory() as folder:
			self._entry(folder, '$Iold', r'C:\Users\other.txt', 1)
			with patch(
				'core.recycle_bin.get_current_user_sid',
				return_value='S-1-5-21-test'
			), \
				patch(
					'core.recycle_bin._recycle_bin_directory',
					return_value=folder
				):
				self.assertIsNone(find_entry(r'C:\Users\a.txt'))

	def _entry(self, folder, name, original_path, hour):
		path = join(folder, name)
		deleted_at = datetime(2024, 1, 2, hour, tzinfo=timezone.utc)
		with open(path, 'wb') as file:
			file.write(_metadata(2, original_path, deleted_at))
		data_path = join(folder, name.replace('$I', '$R'))
		with open(data_path, 'wb') as file:
			file.write(b'abc')
		return RecycleBinEntry(original_path, data_path, path, deleted_at, 3)


class RestoreEntryTest(TestCase):
	def test_restores_data_then_removes_metadata(self):
		with TemporaryDirectory() as folder:
			entry = self._entry(folder)
			with patch(
				'core.recycle_bin.rename', wraps=os.rename
			) as rename, \
				patch('core.recycle_bin.remove', wraps=os.remove) as remove:
				restore_entry(entry)
			self.assertEqual(
				(entry.data_path, entry.original_path), rename.call_args.args
			)
			remove.assert_called_once_with(entry.info_path)
			with open(entry.original_path, 'rb') as file:
				self.assertEqual(b'restored', file.read())

	def test_does_not_overwrite_existing_destination_or_remove_metadata(self):
		with TemporaryDirectory() as folder:
			entry = self._entry(folder)
			with open(entry.original_path, 'wb') as file:
				file.write(b'keep')
			with self.assertRaises(FileExistsError):
				restore_entry(entry)
			self.assertTrue(__import__('os').path.exists(entry.info_path))
			with open(entry.original_path, 'rb') as file:
				self.assertEqual(b'keep', file.read())

	def test_keeps_metadata_when_data_move_fails(self):
		with TemporaryDirectory() as folder:
			entry = self._entry(folder)
			with patch(
				'core.recycle_bin.rename', side_effect=PermissionError
			):
				with self.assertRaises(PermissionError):
					restore_entry(entry)
			self.assertTrue(__import__('os').path.exists(entry.info_path))

	def _entry(self, folder):
		data_path = join(folder, '$Rabc')
		info_path = join(folder, '$Iabc')
		original_path = join(folder, 'original.txt')
		with open(data_path, 'wb') as file:
			file.write(b'restored')
		with open(info_path, 'wb') as file:
			file.write(b'metadata')
		return RecycleBinEntry(
			original_path, data_path, info_path,
			datetime(2024, 1, 2, tzinfo=timezone.utc), 8,
		)


class WindowsTrashRestoreIntegrationTest(TestCase):
	@skipUnless(PLATFORM == 'Windows', 'Windows Recycle Bin only')
	def test_trash_then_restore_returns_file_to_original_path(self):
		with NamedTemporaryFile(delete=False) as file:
			file.write(b'restored')
			path = file.name
		try:
			move_to_trash(path)
			entry = find_entry(path)
			self.assertIsNotNone(entry)
			restore_entry(entry)
			with open(path, 'rb') as file:
				self.assertEqual(b'restored', file.read())
			self.assertFalse(exists(entry.info_path))
		finally:
			if exists(path):
				os.remove(path)
