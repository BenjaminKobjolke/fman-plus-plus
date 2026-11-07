"""Core's setting and dispatch helper for the application transfer queue."""
import fman

from core.settings import get_setting, SETTINGS_FILE


SETTING_KEY = 'queue_transfers'


def is_enabled():
	return get_setting(SETTINGS_FILE, SETTING_KEY, True)


def run_queued(title, fn):
	if is_enabled():
		return fman.run_in_transfer_queue(title, fn)
	return fn()
