"""Close mounted Core views when commands would make them stale.

The tree and viewers sit over the hidden file list. A folder change or an
unsupported command would only change that hidden list, leaving the mounted
view out of sync with the pane.
"""
from core.folder_tree_view import FolderTreeView
from core.imageviewer import PaneImageView
from core.textviewer import PaneTextView
from core.textviewer_pane import confirm_close
from core.videoviewer import PaneVideoView
from fman import DirectoryPane, DirectoryPaneListener
from fman.impl.util.qt.thread import run_in_main_thread

__all__ = ['CloseMountedViewOnLeave']

# Keep the tree's own palette, tab, drop, and toggle commands listed so it can
# operate itself.
TREE_COMMANDS = frozenset({
	'toggle_folder_tree', 'command_palette', 'switch_panes', 'copy', 'move',
	'symlink', 'move_to_trash', 'delete_permanently', 'rename',
	'create_directory', 'copy_paths_to_clipboard', 'copy_file_name',
	'copy_file_path', 'copy_to_clipboard', 'cut', 'paste', 'paste_cut',
	'undo', 'pack', 'open_terminal', 'open_native_file_manager',
	'show_explorer_properties', 'find_locking_processes', 'edit_comment',
	'pin_folder_to_taskbar', 'unpin_folder_from_taskbar', 'open_in_right_pane',
	'open_in_left_pane', 'add_pane', 'remove_pane', 'widen_active_pane',
	'narrow_active_pane', 'show_only_active_pane', 'show_all_panes',
	'set_pane_sizes', 'increase_pane_font_size', 'decrease_pane_font_size',
	'reset_pane_font_size'
})

_CLOSES_ON_FOLDER_CHANGE = (
	FolderTreeView, PaneTextView, PaneImageView, PaneVideoView
)


class CloseMountedViewOnLeave(DirectoryPaneListener):
	def before_location_change(
		self, url: str, sort_column: str = '', ascending: bool = True
	) -> None:
		_close_for_folder_change(self.pane)

	def on_command(self, command_name: str, args: dict) -> None:
		_close_tree_for_command(self.pane, command_name)


@run_in_main_thread
def _close_for_folder_change(pane: DirectoryPane) -> None:
	view = pane.get_mounted_widget()
	if isinstance(view, _CLOSES_ON_FOLDER_CHANGE) and confirm_close(view):
		# shortcut: another listener that rewrites the location re-runs this hook,
		# so a cancelled unsaved-edits prompt can show twice; remember the kept
		# view if users notice.
		pane.unmount_widget()


@run_in_main_thread
def _close_tree_for_command(pane: DirectoryPane, command_name: str) -> None:
	if command_name not in TREE_COMMANDS and isinstance(
		pane.get_mounted_widget(), FolderTreeView
	):
		pane.unmount_widget()
