"""Native Robocopy integration tests for links and filesystem aliases."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
from unittest import skipUnless

from robocopy_plugin import planner, windows

from robocopy_integration_base import RobocopyFixture


@skipUnless(os.name == 'nt', 'robocopy.exe is Windows-only')
class RobocopyLinksIT(RobocopyFixture):
	def test_native_case_sensitive_directory_refused(self):
		library = ctypes.WinDLL('kernel32', use_last_error=True)
		library.SetFileInformationByHandle.argtypes = [
			wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
		]
		library.SetFileInformationByHandle.restype = wintypes.BOOL
		api = windows.api()
		handle = api.CreateFileW(
			str(self.source), 0xc0000000, 7, None, 3, 0x02000000, None
		)
		self.assertNotEqual(ctypes.c_void_p(-1).value, handle)
		try:
			flags = wintypes.DWORD(1)
			if not library.SetFileInformationByHandle(
				handle, 23, ctypes.byref(flags), ctypes.sizeof(flags)
			):
				code = ctypes.get_last_error()
				if code in (1, 5, 50, 87, 1314):
					self.skipTest(
						'Native case-sensitive directory setup unavailable '
						'(Windows error %d)' % code
					)
				raise ctypes.WinError(code)
		finally:
			api.CloseHandle(handle)
		(self.source / 'File.txt').write_bytes(b'upper')
		(self.source / 'file.txt').write_bytes(b'lower')
		self.assertEqual(2, len(list(self.source.iterdir())))
		with self.assertRaisesRegex(ValueError, 'case-sensitive'):
			self.plan(('File.txt', 'file.txt'))
		self.assertFalse(self.destination.exists())

	def test_native_short_alias_refused(self):
		path = self.source / 'long selected filename.txt'
		path.write_bytes(b'keep')
		library = ctypes.WinDLL('kernel32', use_last_error=True)
		library.GetShortPathNameW.argtypes = [
			wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD
		]
		library.GetShortPathNameW.restype = wintypes.DWORD
		buffer = ctypes.create_unicode_buffer(32768)
		if not library.GetShortPathNameW(str(path), buffer, len(buffer)):
			raise ctypes.WinError(ctypes.get_last_error())
		alias = Path(buffer.value).name
		if alias == path.name:
			self.skipTest('8.3 aliases are disabled for this temporary volume')
		with self.assertRaisesRegex(ValueError, '8.3 alias'):
			self.plan((alias,))
		self.assertFalse(self.destination.exists())

	def test_nested_source_junction_exclusion_and_selected_junction_refusal(self):
		folder = self.source / 'Folder'
		folder.mkdir()
		outside = self.root / 'outside'
		outside.mkdir()
		(outside / 'keep.txt').write_bytes(b'outside')
		self.junction(folder / 'excluded', outside)
		self.junction(self.source / 'selected', outside)
		with self.assertRaisesRegex(ValueError, 'junctions'):
			self.plan(('selected',))
		plan = self.plan(('Folder',), move=True)
		self.run_plan(plan)
		self.assertFalse((self.destination / 'Folder' / 'excluded').exists())
		self.assertEqual(b'outside', (outside / 'keep.txt').read_bytes())
		self.assertEqual(1, planner.remaining(plan.jobs[0].entries)[0])

	def test_selected_symlink_refused_and_nested_source_symlinks_excluded(self):
		(self.source / 'Folder').mkdir()
		outside = self.root / 'outside'
		outside.mkdir()
		(outside / 'file.txt').write_bytes(b'outside')
		try:
			os.symlink(
				outside, self.source / 'Folder' / 'directory-link',
				target_is_directory=True
			)
			os.symlink(outside / 'file.txt', self.source / 'Folder' / 'file-link.txt')
			os.symlink(outside, self.source / 'selected-link', target_is_directory=True)
		except OSError as error:
			if getattr(error, 'winerror', None) == 1314:
				self.skipTest('Windows symlink privilege unavailable')
			raise
		with self.assertRaisesRegex(ValueError, 'links'):
			self.plan(('selected-link',))
		self.run_plan(self.plan(('Folder',), move=True))
		self.assertEqual([], list((self.destination / 'Folder').iterdir()))
		self.assertEqual(b'outside', (outside / 'file.txt').read_bytes())
		self.assertTrue((self.source / 'Folder').exists())
