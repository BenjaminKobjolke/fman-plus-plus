import errno
import ctypes
from ctypes import wintypes
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf
from unittest.mock import patch

from fman import PLATFORM
from fman.url import as_url

from core.fs.local import LocalFileSystem
from core.fs.local import locks
from core.fs.local.transfers import CopyFile, LocalTransfers, MoveByCopying


class LockedFileCheckTest(TestCase):
	def test_local_filesystem_resolves_transfer_methods_through_mixin(self):
		for method in ('copy', 'move', 'prepare_copy', 'prepare_move'):
			with self.subTest(method=method):
				self.assertIs(
					getattr(LocalFileSystem, method), getattr(LocalTransfers, method)
				)

	def test_setting_defaults_to_enabled(self):
		with patch.object(locks, 'get_setting', return_value=True) as get_setting:
			self.assertTrue(locks.is_enabled())
		get_setting.assert_called_once_with(
			'Core Settings.json', 'check_locked_files', True
		)

	def test_unlocked_file_is_allowed(self):
		with TemporaryDirectory() as directory:
			path = Path(directory, 'file.txt')
			path.touch()
			with patch.object(locks, 'PLATFORM', 'Windows'), \
					patch.object(locks, 'is_enabled', return_value=True), \
					patch.object(locks, '_open_for_delete') as open_file:
				locks.raise_if_locked(str(path))
			open_file.assert_called_once_with(str(path))

	def test_disabled_setting_skips_check(self):
		with patch.object(locks, 'PLATFORM', 'Windows'), \
				patch.object(locks, 'is_enabled', return_value=False), \
				patch.object(locks, '_open_for_delete') as open_file:
			locks.raise_if_locked('file.txt')
		open_file.assert_not_called()

	@skipIf(PLATFORM != 'Windows', 'Skip Windows-only test')
	def test_locked_open_file_raises_permission_error(self):
		with TemporaryDirectory() as directory:
			path = Path(directory, 'file.txt')
			path.touch()
			kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
			create_file = kernel32.CreateFileW
			create_file.argtypes = (
				wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
				wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
			)
			create_file.restype = wintypes.HANDLE
			close_handle = kernel32.CloseHandle
			close_handle.argtypes = (wintypes.HANDLE,)
			close_handle.restype = wintypes.BOOL
			handle = create_file(
				str(path), 0x80000000, 0x1 | 0x2, None, 3, 0x80, None
			)
			self.assertNotEqual(wintypes.HANDLE(-1).value, handle)
			try:
				with self.assertRaises(PermissionError) as raised:
					locks.raise_if_locked(str(path))
			finally:
				close_handle(handle)
		self.assertEqual(errno.EACCES, raised.exception.errno)
		self.assertEqual(
			'The file is in use by another program', raised.exception.strerror
		)
		self.assertEqual(str(path), raised.exception.filename)

	def test_other_windows_errors_are_left_to_the_operation(self):
		with (
			patch.object(locks, 'PLATFORM', 'Windows'),
			patch.object(locks, 'is_enabled', return_value=True),
			patch.object(
				locks, '_open_for_delete',
				side_effect=OSError(5, 'access denied')
			),
		):
			locks.raise_if_locked('file.txt')

	def test_cross_drive_move_checks_before_copying(self):
		with TemporaryDirectory() as directory:
			src = Path(directory, 'source.txt')
			dst = Path(directory, 'target.txt')
			src.write_text('source')
			dst.write_text('existing target')
			fs = LocalFileSystem()
			task = MoveByCopying(fs, as_url(src), as_url(dst), src.stat().st_size)
			locked_error = PermissionError(errno.EACCES, 'locked', str(src))
			with (
				patch('core.fs.local.locks.is_enabled', return_value=True),
				patch(
					'core.fs.local.locks.raise_if_locked',
					side_effect=locked_error
				) as check,
			):
				with self.assertRaises(PermissionError):
					task()
			check.assert_called_once_with(str(src))
			self.assertEqual('source', src.read_text())
			self.assertEqual('existing target', dst.read_text())

	def test_existing_copy_target_is_checked_before_write(self):
		with TemporaryDirectory() as directory:
			src = Path(directory, 'source.txt')
			dst = Path(directory, 'target.txt')
			src.write_text('source')
			dst.write_text('existing target')
			fs = LocalFileSystem()
			task = CopyFile(fs, as_url(src), as_url(dst), src.stat().st_size)
			locked_error = PermissionError(errno.EACCES, 'locked', str(dst))
			with (
				patch('core.fs.local.locks.is_enabled', return_value=True),
				patch(
					'core.fs.local.locks.raise_if_locked',
					side_effect=locked_error
				) as check,
			):
				with self.assertRaises(PermissionError):
					task()
			check.assert_called_once_with(str(dst))
			self.assertEqual('existing target', dst.read_text())

