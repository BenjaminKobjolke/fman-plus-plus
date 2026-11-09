from core.column_visibility import (
	COLUMN_SETTINGS, is_column_hidden, set_column_hidden,
	shows_name_without_extension,
)
from unittest import TestCase
from unittest.mock import call, patch

class ColumnVisibilityTest(TestCase):
	def test_plugin_columns_are_visible_by_default(self):
		with patch('core.column_visibility.get_setting', return_value=[]):
			self.assertFalse(is_column_hidden('plugin.Status'))

	def test_plugin_column_visibility_is_stored_in_hidden_columns(self):
		hidden = []
		saved = []
		def get_setting(_file, _key, _default):
			return hidden
		def save_setting(_file, _key, value):
			saved.append(call('Core Settings.json', 'hidden_columns', value[:]))
			hidden[:] = value
		with patch(
			'core.column_visibility.get_setting', side_effect=get_setting
		) as get, patch(
			'core.column_visibility.save_setting', side_effect=save_setting
		):
			set_column_hidden('plugin.Status', True)
			set_column_hidden('plugin.Other', True)
			set_column_hidden('plugin.Status', False)

		self.assertEqual(
			[call('Core Settings.json', 'hidden_columns', ['plugin.Status']),
			 call(
				'Core Settings.json', 'hidden_columns',
				['plugin.Status', 'plugin.Other'],
			 ),
			 call('Core Settings.json', 'hidden_columns', ['plugin.Other'])],
			saved,
		)
		self.assertEqual(3, get.call_count)

	def test_existing_columns_keep_their_settings_keys(self):
		with patch('core.column_visibility.save_setting') as save:
			for name, (key, _) in COLUMN_SETTINGS.items():
				set_column_hidden(name, True)
				self.assertEqual(('Core Settings.json', key, True), save.call_args.args)

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
			self.assertFalse(is_column_hidden('core.file_columns.Comment'))

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
