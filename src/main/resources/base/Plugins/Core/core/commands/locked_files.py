"""Command for enabling or disabling the per-file Windows lock check."""
from core.fs.local.locks import is_enabled, SETTING_KEY
from core.settings import save_setting, SETTINGS_FILE
from fman import ApplicationCommand, show_status_message


__all__ = ['ToggleLockedFileCheck']


class ToggleLockedFileCheck(ApplicationCommand):
	aliases = ('Toggle locked file check',)

	def __call__(self):
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, SETTING_KEY, enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Locked file check: ' + state, timeout_secs=3)
