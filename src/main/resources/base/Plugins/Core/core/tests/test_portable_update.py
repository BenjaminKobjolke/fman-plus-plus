import os
import tempfile
import zipfile
from unittest import TestCase
from unittest.mock import patch

from core import portable_update


class ExtractUpdateTest(TestCase):
	def test_extracts_portable_archive_and_clears_destination(self):
		with tempfile.TemporaryDirectory() as directory:
			archive = os.path.join(directory, 'update.zip')
			dest_dir = os.path.join(directory, 'extracted')
			os.mkdir(dest_dir)
			with open(os.path.join(dest_dir, 'old.txt'), 'w') as old_file:
				old_file.write('old')
			with zipfile.ZipFile(archive, 'w') as update:
				update.writestr('fman++/fman.exe', 'new executable')
				update.writestr('fman++/Plugins/Core/core.py', 'new plugin')

			result = portable_update.extract_update(archive, dest_dir)

			self.assertEqual(os.path.join(dest_dir, 'fman++'), result)
			self.assertTrue(os.path.isfile(os.path.join(result, 'fman.exe')))
			self.assertFalse(os.path.exists(os.path.join(dest_dir, 'old.txt')))

	def test_rejects_archive_without_expected_executable(self):
		with tempfile.TemporaryDirectory() as directory:
			archive = os.path.join(directory, 'invalid.zip')
			with zipfile.ZipFile(archive, 'w') as update:
				update.writestr('other/fman.exe', 'wrong layout')

			with self.assertRaises(ValueError):
				portable_update.extract_update(archive, os.path.join(directory, 'out'))

	def test_rejects_archive_with_path_traversal(self):
		with tempfile.TemporaryDirectory() as directory:
			archive = os.path.join(directory, 'invalid.zip')
			with zipfile.ZipFile(archive, 'w') as update:
				update.writestr('fman++/fman.exe', 'new executable')
				update.writestr('../outside.txt', 'outside')

			with self.assertRaises(ValueError):
				portable_update.extract_update(archive, os.path.join(directory, 'out'))
			self.assertFalse(os.path.exists(os.path.join(directory, 'outside.txt')))


class StartSwapTest(TestCase):
	def test_copies_helper_to_temp_and_launches_detached_swap(self):
		with tempfile.TemporaryDirectory() as directory:
			with patch.object(
					portable_update.tempfile, 'gettempdir', return_value=directory
			), patch.object(portable_update.subprocess, 'Popen') as popen:
				portable_update.start_swap('C:/update/fman++', 'C:/fman++')

			expected_helper = os.path.join(directory, 'portable_update.ps1')
			self.assertTrue(os.path.isfile(expected_helper))
			args, kwargs = popen.call_args
			self.assertEqual('powershell', args[0][0])
			self.assertIn('-NoProfile', args[0])
			self.assertIn('-ExecutionPolicy', args[0])
			self.assertIn('-WindowStyle', args[0])
			self.assertIn('-File', args[0])
			self.assertEqual(expected_helper, args[0][args[0].index('-File') + 1])
			for flag, value in (
				('-Source', 'C:/update/fman++'),
				('-Target', 'C:/fman++'),
				('-RestartPath', os.path.join('C:/fman++', 'fman.exe')),
			):
				self.assertEqual(value, args[0][args[0].index(flag) + 1])
			self.assertEqual(os.getpid(), int(args[0][args[0].index('-ProcessId') + 1]))
			self.assertTrue(kwargs['creationflags'])
