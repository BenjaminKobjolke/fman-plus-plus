"""Command for enabling or disabling the read-only replacement question."""
from core.read_only_overwrite import is_enabled, SETTING_KEY
from core.settings import save_setting, SETTINGS_FILE
from fman import ApplicationCommand, show_status_message


__all__ = ['ToggleReadOnlyReplaceQuestion']


class ToggleReadOnlyReplaceQuestion(ApplicationCommand):
	aliases = ('Toggle read-only replace question',)

	def __call__(self):
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, SETTING_KEY, enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Read-only replace question: ' + state, timeout_secs=3)
