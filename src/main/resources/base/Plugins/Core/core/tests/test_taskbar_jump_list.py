from unittest import TestCase, skipUnless
from unittest.mock import patch

from fman import PLATFORM

from core.taskbar_jump_list import launch_arguments, surviving_paths


class LaunchArgumentsTest(TestCase):
	def test_quotes_plain_path_and_path_with_spaces(self):
		with patch('core.taskbar_jump_list.is_frozen', return_value=True):
			self.assertEqual('C:\\folder', launch_arguments('C:\\folder'))
			self.assertEqual(
				'"C:\\my folder"', launch_arguments('C:\\my folder')
			)

	def test_quotes_drive_root_with_trailing_backslash(self):
		with patch('core.taskbar_jump_list.is_frozen', return_value=True):
			self.assertEqual('"C:\\\\"', launch_arguments('C:\\'))

	def test_adds_script_path_when_not_frozen(self):
		with patch('core.taskbar_jump_list.is_frozen', return_value=False), \
				patch('core.taskbar_jump_list.sys.argv', ['C:\\my app.py']):
			self.assertEqual(
				'"C:\\my app.py" C:\\folder',
				launch_arguments('C:\\folder')
			)


class SurvivingPathsTest(TestCase):
	def test_drops_removed_paths_case_insensitively_and_keeps_order(self):
		saved = [r'C:\One', r'C:\Two', r'C:\Three']
		removed = [r'c:\tWo']
		self.assertEqual(
			[r'C:\One', r'C:\Three'], surviving_paths(saved, removed)
		)


@skipUnless(PLATFORM == 'Windows', 'The Windows jump list API is required.')
class RebuildJumpListTest(TestCase):
	def test_rebuilds_two_folder_category_with_throwaway_app_id(self):
		from win32com.shell import shell
		from core import taskbar_jump_list
		app_id = 'fman.tests.taskbar_jump_list'
		with patch.object(taskbar_jump_list, '_APP_ID_FOR_TESTS', app_id):
			try:
				taskbar_jump_list.rebuild([r'C:\One', r'C:\Two'])
			finally:
				pythoncom = __import__('pythoncom')
				pythoncom.CoInitialize()
				try:
					destination_list = pythoncom.CoCreateInstance(
						shell.CLSID_DestinationList, None,
						pythoncom.CLSCTX_INPROC_SERVER,
						shell.IID_ICustomDestinationList
					)
					destination_list.SetAppID(app_id)
					destination_list.DeleteList(None)
				finally:
					pythoncom.CoUninitialize()
