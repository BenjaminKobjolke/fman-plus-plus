"""Commands for opening and configuring the folder tree pane view."""
from core.commands.hidden_files import _is_showing_hidden_files
from core.commands.pane_view import PANE_FONT_SIZE_KEY
from core.commands.transfer import drop_command
from core.commands.util import get_opposite_pane
from core.font_size import get_saved_font_size
from core.folder_tree import FOLLOW_CURSOR_KEY, tree_ancestors
from core.folder_tree_view import FolderTreeActions, FolderTreeView
from core.settings import get_setting, save_setting, SETTINGS_FILE
from core.textviewer_pane import begin_new_view
from fman import ApplicationCommand, DirectoryPaneCommand, show_status_message
from fman.impl.view.backgrounds import TRANSPARENT_PROPERTY, set_transparent
from fman.impl.util.qt.thread import run_in_main_thread

__all__ = ['ToggleFolderTree', 'ToggleTreeFollowsCursor']
_FolderTreeView = FolderTreeView
_COMMAND_PALETTE = 'command_palette'


class ToggleFolderTree(DirectoryPaneCommand):
	aliases = ('Toggle folder tree',)
	@run_in_main_thread
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
		widget = self.pane._widget
		actions = FolderTreeActions(
			navigate, self.pane.unmount_widget, drop,
			lambda: self.pane.run_command('switch_panes'),
			lambda: self.pane.run_command(_COMMAND_PALETTE),
			lambda event: widget._controller.handle_shortcut(widget, event)
		)
		view = FolderTreeView(
			_is_showing_hidden_files(self.pane), actions,
			get_setting(SETTINGS_FILE, FOLLOW_CURSOR_KEY, False),
			widget._model._fs._icon_provider,
			widget, fs=widget._model._fs
		)
		file_view = self.pane._widget._view_mode.visible_view()
		view.set_font_size(get_saved_font_size(PANE_FONT_SIZE_KEY))
		view.viewport().setAutoFillBackground(False)
		set_transparent(
			view, file_view.property(TRANSPARENT_PROPERTY)
		)
		path = self.pane.get_path()
		self.pane.mount_widget(view)
		view.open_to(tree_ancestors(path))


class ToggleTreeFollowsCursor(ApplicationCommand):
	aliases = ('Toggle tree follows cursor',)
	@run_in_main_thread
	def __call__(self):
		enabled = not get_setting(SETTINGS_FILE, FOLLOW_CURSOR_KEY, False)
		save_setting(SETTINGS_FILE, FOLLOW_CURSOR_KEY, enabled)
		for pane in self.window.get_panes():
			view = pane.get_mounted_widget()
			if isinstance(view, _FolderTreeView):
				view.set_follow_cursor(enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Tree follows cursor: ' + state, timeout_secs=3)
