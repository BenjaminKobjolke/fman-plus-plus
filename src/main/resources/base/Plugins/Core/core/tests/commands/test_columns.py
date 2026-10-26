from core.commands.columns import _get_hidden_flags
from unittest import TestCase
from unittest.mock import patch

class GetHiddenFlagsTest(TestCase):
	def test_hides_size_and_modified_columns(self):
		with patch('core.commands.columns.get_setting', return_value=True):
			flags = _get_hidden_flags(
				['core.Name', 'core.Size', 'core.Modified']
			)
		self.assertEqual([False, True, True], flags)

	def test_does_not_hide_columns_unique_to_drives_view(self):
		columns = [
			'core.fs.local.windows.drives.DriveName',
			'core.fs.local.windows.drives.DriveSize',
			'core.fs.local.windows.drives.DriveFree',
		]
		with patch('core.commands.columns.get_setting', return_value=True):
			flags = _get_hidden_flags(columns)
		self.assertEqual([False, False, False], flags)
