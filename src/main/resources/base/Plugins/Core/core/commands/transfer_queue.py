"""Command for enabling or disabling the transfer queue."""
from core.settings import save_setting, SETTINGS_FILE
from core.transfer_queue import is_enabled, SETTING_KEY
from fman import ApplicationCommand, show_status_message


__all__ = ['ToggleTransferQueue']


class ToggleTransferQueue(ApplicationCommand):
	aliases = ('Toggle transfer queue',)

	def __call__(self):
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, SETTING_KEY, enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Transfer queue: ' + state, timeout_secs=3)
