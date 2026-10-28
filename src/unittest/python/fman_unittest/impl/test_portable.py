import os
import sys
import tempfile
from unittest import TestCase
from unittest.mock import patch

from fman.impl import portable


class PortableProfileTest(TestCase):
	def test_marker_in_frozen_windows_app_selects_data_directory(self):
		with tempfile.TemporaryDirectory() as app_dir:
			with open(os.path.join(app_dir, portable.MARKER_NAME), 'w'):
				pass
			executable = os.path.join(app_dir, 'fman.exe')
			with patch.object(sys, 'platform', 'win32'), \
				 patch.object(sys, 'frozen', True, create=True), \
				 patch.object(sys, 'executable', executable):
				self.assertEqual(app_dir, portable.portable_app_dir())
				self.assertEqual(
					os.path.join(app_dir, portable.DATA_FOLDER_NAME),
					portable.portable_data_directory(),
				)

	def test_missing_marker_disables_portable_profile(self):
		with tempfile.TemporaryDirectory() as app_dir:
			with patch.object(sys, 'platform', 'win32'), \
				 patch.object(sys, 'frozen', True, create=True), \
				 patch.object(sys, 'executable', os.path.join(app_dir, 'fman.exe')):
				self.assertIsNone(portable.portable_app_dir())
				self.assertIsNone(portable.portable_data_directory())

	def test_non_frozen_run_is_not_portable(self):
		with tempfile.TemporaryDirectory() as app_dir:
			with open(os.path.join(app_dir, portable.MARKER_NAME), 'w'):
				pass
			with patch.object(sys, 'platform', 'win32'), \
				 patch.object(sys, 'frozen', False, create=True), \
				 patch.object(sys, 'executable', os.path.join(app_dir, 'fman.exe')):
				self.assertIsNone(portable.portable_app_dir())

	def test_check_writable_creates_directory(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			data_dir = os.path.join(temp_dir, portable.DATA_FOLDER_NAME)
			self.assertIsNone(portable.check_writable(data_dir))
			self.assertTrue(os.path.isdir(data_dir))

	def test_check_writable_returns_error_when_parent_is_file(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			parent_file = os.path.join(temp_dir, 'file')
			with open(parent_file, 'w'):
				pass
			error = portable.check_writable(os.path.join(parent_file, 'Data'))
			self.assertIsInstance(error, OSError)
