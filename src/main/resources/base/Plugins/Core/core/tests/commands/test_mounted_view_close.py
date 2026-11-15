from core.commands.mounted_view_close import CloseMountedViewOnLeave, TREE_COMMANDS
from core.folder_tree_view import FolderTreeView
from core.imageviewer import PaneImageView
from core.textviewer import PaneTextView
from core.videoviewer import PaneVideoView
import core
from fman import DirectoryPane
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import MagicMock, patch

# The main-thread decorator needs a QApplication instance; keep it alive for
# the duration of these command tests.
_APP = QApplication.instance() or QApplication([])


class CloseMountedViewOnLeaveTest(TestCase):
	def setUp(self):
		self.pane = MagicMock(spec=DirectoryPane)
		self.listener = CloseMountedViewOnLeave(self.pane)

	def test_folder_change_unmounts_tree_and_returns_none(self):
		self.pane.get_mounted_widget.return_value = MagicMock(spec=FolderTreeView)

		self.assertIsNone(self.listener.before_location_change('drives://'))

		self.pane.unmount_widget.assert_called_once_with()

	def test_folder_change_confirms_before_unmounting_text_viewer(self):
		self.pane.get_mounted_widget.return_value = MagicMock(spec=PaneTextView)
		with patch('core.commands.mounted_view_close.confirm_close', return_value=True):
			self.listener.before_location_change('file:///next')
		self.pane.unmount_widget.assert_called_once_with()

	def test_cancelled_text_viewer_close_keeps_viewer_mounted(self):
		self.pane.get_mounted_widget.return_value = MagicMock(spec=PaneTextView)
		with patch(
			'core.commands.mounted_view_close.confirm_close', return_value=False
		):
			self.listener.before_location_change('file:///next')
		self.pane.unmount_widget.assert_not_called()

	def test_folder_change_unmounts_image_and_video_viewers(self):
		for view_type in (PaneImageView, PaneVideoView):
			with self.subTest(view_type=view_type):
				self.pane.reset_mock()
				self.pane.get_mounted_widget.return_value = MagicMock(spec=view_type)
				self.listener.before_location_change('file:///next')
				self.pane.unmount_widget.assert_called_once_with()

	def test_folder_change_leaves_foreign_or_empty_mount_alone(self):
		for view in (MagicMock(), None):
			with self.subTest(view=view):
				self.pane.reset_mock()
				self.pane.get_mounted_widget.return_value = view
				self.listener.before_location_change('file:///next')
				self.pane.unmount_widget.assert_not_called()

	def test_unsupported_command_unmounts_tree_and_returns_none(self):
		self.pane.get_mounted_widget.return_value = MagicMock(spec=FolderTreeView)

		self.assertIsNone(self.listener.on_command('show_volumes', {}))

		self.pane.unmount_widget.assert_called_once_with()

	def test_supported_tree_commands_leave_tree_mounted(self):
		for command_name in ('copy', 'toggle_folder_tree', 'command_palette'):
			with self.subTest(command_name=command_name):
				self.pane.reset_mock()
				self.pane.get_mounted_widget.return_value = MagicMock(
					spec=FolderTreeView
				)
				self.listener.on_command(command_name, {})
				self.pane.unmount_widget.assert_not_called()

	def test_unsupported_command_does_not_unmount_text_viewer(self):
		self.pane.get_mounted_widget.return_value = MagicMock(spec=PaneTextView)

		self.listener.on_command('show_volumes', {})

		self.pane.unmount_widget.assert_not_called()

	def test_every_tree_command_is_exported_by_core(self):
		for name in TREE_COMMANDS:
			with self.subTest(name=name):
				class_name = ''.join(part.title() for part in name.split('_'))
				self.assertTrue(hasattr(core, class_name), class_name)
