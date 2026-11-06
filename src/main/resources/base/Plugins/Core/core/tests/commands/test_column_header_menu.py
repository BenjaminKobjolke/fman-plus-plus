from core.commands.column_header_menu import install_header_menu
from unittest import TestCase
from unittest.mock import Mock, patch

class ColumnHeaderMenuTest(TestCase):
	def test_menu_lists_plugin_columns_but_not_column_zero(self):
		header = Mock()
		pane = Mock()
		pane.get_columns.return_value = ['core.Name', 'plugin.Status', 'core.Size']
		pane._widget._file_view.horizontalHeader.return_value = header
		menu = Mock()
		actions = []
		def action(name, parent):
			result = Mock()
			result.name = name
			actions.append(result)
			return result
		with patch(
			'core.commands.column_header_menu.Menu', return_value=menu
		), patch(
			'core.commands.column_header_menu.QAction', side_effect=action
		), patch(
			'core.commands.column_header_menu.is_column_hidden',
			return_value=False,
		):
			install_header_menu.__wrapped__(pane, Mock())
			header.customContextMenuRequested.connect.call_args.args[0](Mock())

		self.assertEqual(['Status', 'Size'], [item.name for item in actions])
