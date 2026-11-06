from core.commands.columns import (
	_get_hidden_flags, SortByColumn, ToggleFixedColumnWidths,
)
from unittest import TestCase
from unittest.mock import Mock, call, patch

class GetHiddenFlagsTest(TestCase):
	def test_hides_size_and_modified_columns(self):
		with patch('core.column_visibility.get_setting', return_value=True):
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
		with patch(
			'core.column_visibility.get_setting',
			side_effect=lambda _file, key, default: (
				True if key != 'hidden_columns' else []
			),
		):
			flags = _get_hidden_flags(columns)
		self.assertEqual([False, False, False], flags)

	def test_plugin_column_can_be_hidden_but_column_zero_stays_visible(self):
		with patch(
			'core.column_visibility.get_setting',
			side_effect=lambda _file, key, default: ['plugin.Status']
			if key == 'hidden_columns' else default,
		):
			flags = _get_hidden_flags(['plugin.Name', 'plugin.Status'])
		self.assertEqual([False, True], flags)

class SortByColumnTest(TestCase):
	def test_quicksearch_uses_only_visible_columns_and_current_visible_index(
		self,
	):
		class Pane:
			def get_columns(self):
				return ['core.Name', 'core.Extension', 'core.Modified']
			def get_sort_column(self): return 'core.Modified', True
		pane = Pane()
		with patch(
			'core.commands.columns._get_hidden_flags',
			return_value=[False, True, False],
		), patch(
			'core.commands.columns.show_quicksearch', return_value=None
		) as quicksearch:
			SortByColumn(pane)()
		get_items = quicksearch.call_args.args[0]
		self.assertEqual(1, quicksearch.call_args.kwargs['item'])
		self.assertEqual(
			['core.Name', 'core.Modified'], [item.value for item in get_items('')]
		)

class ToggleFixedColumnWidthsTest(TestCase):
	def test_toggles_setting_and_reapplies_visibility_to_every_pane(self):
		panes = [object(), object()]
		window = Mock()
		window.get_panes.return_value = panes
		command = ToggleFixedColumnWidths(Mock(window=window))
		with patch(
			'core.commands.columns.get_setting', side_effect=[True, False]
		), patch('core.commands.columns.save_setting') as save_setting, patch(
			'core.commands.columns._apply_column_visibility'
		) as apply_visibility:
			command()
			command()

		self.assertEqual([
			call('Core Settings.json', 'fit_name_column', False),
			call('Core Settings.json', 'fit_name_column', True),
		], save_setting.call_args_list)
		self.assertEqual(
			[call(pane) for pane in panes] * 2,
			apply_visibility.call_args_list,
		)
