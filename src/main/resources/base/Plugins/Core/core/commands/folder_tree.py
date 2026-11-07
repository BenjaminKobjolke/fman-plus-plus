"""Commands for opening and configuring the folder tree pane view."""
from core.commands.hidden_files import _is_showing_hidden_files
from core.commands.transfer import drop_command
from core.commands.util import get_opposite_pane
from core.folder_tree import FOLLOW_CURSOR_KEY, tree_ancestors
from core.folder_tree_view import FolderTreeActions, FolderTreeView
from core.settings import get_setting, save_setting, SETTINGS_FILE
from core.textviewer_pane import begin_new_view
from fman import ApplicationCommand, DirectoryPaneCommand, show_status_message

__all__ = ['ToggleFolderTree', 'ToggleTreeFollowsCursor']
_FolderTreeView = FolderTreeView


class ToggleFolderTree(DirectoryPaneCommand):
	aliases = ('Toggle folder tree',)
	def __call__(self):
		if isinstance(self.pane.get_mounted_widget(), _FolderTreeView):
			self.pane.unmount_widget()
			return
		if begin_new_view(self.pane) is None:
			return
		def navigate(url):
			panes = self.pane.window.get_panes()
			if len(panes) == 1:
				self.pane.unmount_widget()
				self.pane.set_path(url)
			else:
				get_opposite_pane(self.pane).set_path(url)
		def drop(urls, dest_dir, is_copy):
			self.pane.run_command(
				drop_command(urls, dest_dir, is_copy),
				{'files': urls, 'dest_dir': dest_dir}
			)
		actions = FolderTreeActions(navigate, self.pane.unmount_widget, drop)
		view = FolderTreeView(
			_is_showing_hidden_files(self.pane), actions,
			get_setting(SETTINGS_FILE, FOLLOW_CURSOR_KEY, False),
			self.pane.get_colors(), self.pane._widget
		)
		self.pane.mount_widget(view)
		view.open_to(tree_ancestors(self.pane.get_path()))


class ToggleTreeFollowsCursor(ApplicationCommand):
	aliases = ('Toggle tree follows cursor',)
	def __call__(self):
		enabled = not get_setting(SETTINGS_FILE, FOLLOW_CURSOR_KEY, False)
		save_setting(SETTINGS_FILE, FOLLOW_CURSOR_KEY, enabled)
		for pane in self.window.get_panes():
			view = pane.get_mounted_widget()
			if isinstance(view, _FolderTreeView):
				view.set_follow_cursor(enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Tree follows cursor: ' + state, timeout_secs=3)
