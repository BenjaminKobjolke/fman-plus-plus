from core.commands.places import _env_dir
from core.commands.util import shell_folder
from os.path import expanduser
from unittest import TestCase, skipUnless
from unittest.mock import patch

import os

from fman import DATA_DIRECTORY, PLATFORM

class GoToPluginsDirectoryTest(TestCase):
	def test_is_plugins_folder_in_data_directory(self):
		from core.commands.places import GoToPluginsDirectory

		self.assertEqual(
			os.path.join(DATA_DIRECTORY, 'Plugins'),
			GoToPluginsDirectory(None).get_directory()
		)

class EnvDirTest(TestCase):
	def test_unset_variable_is_none(self):
		# None means "no such place on this machine", which is what makes the
		# command hide itself instead of offering a dead row.
		with patch.dict(os.environ, {}, clear=True):
			self.assertIsNone(_env_dir('FMAN_TEST_NOT_SET'))
	def test_empty_variable_is_none(self):
		with patch.dict(os.environ, {'FMAN_TEST_EMPTY': ''}):
			self.assertIsNone(_env_dir('FMAN_TEST_EMPTY'))
	def test_set_variable(self):
		with patch.dict(os.environ, {'FMAN_TEST_DIR': r'C:\Some\Dir'}):
			self.assertEqual(r'C:\Some\Dir', _env_dir('FMAN_TEST_DIR'))

class ShellFolderTest(TestCase):
	@skipUnless(PLATFORM == 'Windows', 'The registry only exists on Windows.')
	def test_falls_back_when_registry_read_fails(self):
		import winreg
		with patch.object(winreg, 'OpenKey', side_effect=OSError):
			self.assertEqual(
				expanduser('~/Desktop'), shell_folder('Desktop', '~/Desktop')
			)
	@skipUnless(PLATFORM == 'Windows', 'The registry only exists on Windows.')
	def test_registry_value_wins(self):
		# The whole point of the registry lookup: OneDrive moves Desktop away
		# from ~/Desktop, and only the registry knows where to.
		with patch(
			'core.commands.util._query_shell_folder',
			return_value=r'C:\Users\me\OneDrive\Desktop'
		):
			self.assertEqual(
				r'C:\Users\me\OneDrive\Desktop',
				shell_folder('Desktop', '~/Desktop')
			)
	@skipUnless(PLATFORM != 'Windows', 'Tests the non-Windows code path.')
	def test_fallback_on_other_platforms(self):
		self.assertEqual(
			expanduser('~/Desktop'), shell_folder('Desktop', '~/Desktop')
		)
