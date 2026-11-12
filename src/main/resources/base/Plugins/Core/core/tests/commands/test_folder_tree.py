from core.commands.folder_tree import ToggleFolderTree, ToggleTreeFollowsCursor
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import MagicMock, Mock, call, patch

# The main-thread decorator needs a QApplication instance; keep it alive for
# the duration of these command tests.
_APP = QApplication.instance() or QApplication([])


class ToggleFolderTreeTest(TestCase):
	def test_mounts_tree_and_navigates_opposite_pane(self):
		pane, other = MagicMock(), MagicMock()
		pane.window.get_panes.return_value = [pane, other]
		pane.get_path.return_value = 'file:///current'
		view = MagicMock()
		with patch('core.commands.folder_tree.begin_new_view'), \
			patch(
				'core.commands.folder_tree.FolderTreeView', return_value=view
			) as factory, \
			patch(
				'core.commands.folder_tree._is_showing_hidden_files', return_value=False
			), \
			patch('core.commands.folder_tree.get_setting', return_value=False), \
			patch(
				'core.commands.folder_tree.tree_ancestors',
				return_value=['file:///', 'file:///current'],
			):
			ToggleFolderTree(pane)()
		pane.mount_widget.assert_called_once_with(view)
		view.open_to.assert_called_once_with(['file:///', 'file:///current'])
		actions = factory.call_args.args[1]
		actions.navigate('file:///chosen')
		other.set_path.assert_called_once_with('file:///chosen')
		actions.switch_panes()
		pane.run_command.assert_called_once_with('switch_panes')
	def test_single_pane_unmounts_before_navigating(self):
		pane = MagicMock()
		pane.window.get_panes.return_value = [pane]
		view = MagicMock()
		with patch('core.commands.folder_tree.begin_new_view'), \
			patch(
				'core.commands.folder_tree.FolderTreeView', return_value=view
			) as factory, \
			patch(
				'core.commands.folder_tree._is_showing_hidden_files', return_value=False
			), \
			patch('core.commands.folder_tree.get_setting', return_value=False), \
			patch('core.commands.folder_tree.tree_ancestors', return_value=['file:///']):
			ToggleFolderTree(pane)()
		factory.call_args.args[1].navigate('file:///chosen')
		pane.unmount_widget.assert_called_once_with()
		pane.set_path.assert_called_once_with('file:///chosen')
	def test_cancelled_view_replacement_leaves_pane_unchanged(self):
		pane = MagicMock()
		with patch('core.commands.folder_tree.begin_new_view', return_value=None):
			ToggleFolderTree(pane)()
		pane.mount_widget.assert_not_called()


class ToggleTreeFollowsCursorTest(TestCase):
	def test_toggles_saved_setting_and_reports_state(self):
		class FakeTree:
			def __init__(self):
				self.set_follow_cursor = Mock()
		window = MagicMock()
		pane = MagicMock()
		view = FakeTree()
		pane.get_mounted_widget.return_value = view
		window.get_panes.return_value = [pane]
		with patch('core.commands.folder_tree._FolderTreeView', FakeTree), \
			patch('core.commands.folder_tree.get_setting', side_effect=(False, True)), \
			patch('core.commands.folder_tree.save_setting') as save_setting, \
			patch('core.commands.folder_tree.show_status_message') as show_status:
			command = ToggleTreeFollowsCursor(window)
			command()
			command()
		save_setting.assert_has_calls([
			(('Core Settings.json', 'tree_follow_cursor', True),),
			(('Core Settings.json', 'tree_follow_cursor', False),),
		])
		self.assertEqual(2, show_status.call_count)
		view.set_follow_cursor.assert_has_calls([call(True), call(False)])
