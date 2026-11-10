"""Commands that control the built-in file-age shading."""
from core.file_age import (
	FILE_AGE_SHADING_SETTING, apply, is_enabled,
)
from core.settings import save_setting, SETTINGS_FILE
from fman import ApplicationCommand, DirectoryPaneListener, show_status_message


__all__ = ['InitFileAgeShading', 'ToggleFileAgeShading']


class ToggleFileAgeShading(ApplicationCommand):
	aliases = ('Toggle file age shading',)

	def __call__(self):
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, FILE_AGE_SHADING_SETTING, enabled)
		for pane in self.window.get_panes():
			apply(pane)
		state = 'on' if enabled else 'off'
		show_status_message('File age shading: ' + state, timeout_secs=3)


class InitFileAgeShading(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		apply(self.pane)

	def on_path_changed(self):
		apply(self.pane)
