"""Setting and command for deselecting each file once a copy has finished it."""
from core.settings import get_setting, save_setting, SETTINGS_FILE
from fman import ApplicationCommand, show_status_message


__all__ = ['ToggleDeselectAfterTransfer']

SETTING_KEY = 'deselect_after_transfer'


def is_enabled():
	return get_setting(SETTINGS_FILE, SETTING_KEY, True)


class ToggleDeselectAfterTransfer(ApplicationCommand):
	aliases = ('Toggle deselect after copy',)

	def __call__(self):
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, SETTING_KEY, enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Deselect after copy: ' + state, timeout_secs=3)
