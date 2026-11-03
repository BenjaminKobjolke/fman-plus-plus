from core.column_visibility import is_column_hidden, shows_name_without_extension
from unittest import TestCase
from unittest.mock import patch

class ColumnVisibilityTest(TestCase):
	def test_existing_columns_are_visible_and_new_columns_hidden_by_default(self):
		with patch(
			'core.column_visibility.get_setting',
			side_effect=lambda _file, _key, default: default,
		):
			self.assertFalse(is_column_hidden('core.Size'))
			self.assertFalse(is_column_hidden('core.Modified'))
			for name in (
				'core.file_columns.Extension', 'core.file_columns.Version',
				'core.file_columns.Attributes',
			):
				self.assertTrue(is_column_hidden(name))

	def test_name_setting_only_applies_when_extension_column_is_visible(self):
		with (
			patch('core.column_visibility.get_setting', return_value=True),
			patch('core.column_visibility.is_column_hidden', return_value=False),
		):
			self.assertTrue(shows_name_without_extension())
		with patch('core.column_visibility.get_setting', return_value=False):
			self.assertFalse(shows_name_without_extension())
		with (
			patch('core.column_visibility.get_setting', return_value=True),
			patch('core.column_visibility.is_column_hidden', return_value=True),
		):
			self.assertFalse(shows_name_without_extension())
