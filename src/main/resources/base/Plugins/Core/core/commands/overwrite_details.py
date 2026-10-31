"""Command for showing or hiding overwrite file details."""
from core.overwrite_details import is_enabled, SETTING_KEY
from core.settings import save_setting, SETTINGS_FILE
from fman import ApplicationCommand, show_status_message


__all__ = ['ToggleOverwriteDetails']


class ToggleOverwriteDetails(ApplicationCommand):
	aliases = ('Toggle overwrite details',)

	def __call__(self):
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, SETTING_KEY, enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Overwrite details: ' + state, timeout_secs=3)
