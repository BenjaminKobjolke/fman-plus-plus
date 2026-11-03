"""Command-palette settings for unattended Windows updates."""
from core.auto_update import (
	AUTO_UPDATE_INTERVAL_SETTING, AUTO_UPDATE_SETTING,
	MAX_INTERVAL_HOURS, MIN_INTERVAL_HOURS,
	UNSUPPORTED_MESSAGE, interval_hours, is_enabled, is_supported,
)
from core.settings import save_setting, SETTINGS_FILE
from fman import ApplicationCommand, show_alert, show_prompt, show_status_message

__all__ = ['ToggleAutomaticUpdates', 'SetAutomaticUpdateInterval']

INTERVAL_PROMPT = 'Automatic update interval in hours (1–720):'
INVALID_INTERVAL_MESSAGE = 'Enter an interval from 1 to 720 hours.'


class ToggleAutomaticUpdates(ApplicationCommand):
	aliases = ('Toggle automatic updates',)

	def __call__(self):
		if not is_supported():
			show_alert(UNSUPPORTED_MESSAGE)
			return
		enabled = not is_enabled()
		save_setting(SETTINGS_FILE, AUTO_UPDATE_SETTING, enabled)
		state = 'on' if enabled else 'off'
		show_status_message('Automatic updates: ' + state, timeout_secs=3)


class SetAutomaticUpdateInterval(ApplicationCommand):
	aliases = ('Set automatic update interval',)

	def __call__(self):
		if not is_supported():
			show_alert(UNSUPPORTED_MESSAGE)
			return
		value, accepted = show_prompt(
			INTERVAL_PROMPT, str(interval_hours())
		)
		if not accepted:
			return
		try:
			hours = int(value.strip())
		except (AttributeError, ValueError):
			show_alert(INVALID_INTERVAL_MESSAGE)
			return
		if not MIN_INTERVAL_HOURS <= hours <= MAX_INTERVAL_HOURS:
			show_alert(INVALID_INTERVAL_MESSAGE)
			return
		save_setting(SETTINGS_FILE, AUTO_UPDATE_INTERVAL_SETTING, hours)
		show_status_message(
			'Automatic update interval: %d hours' % hours, timeout_secs=3
		)
