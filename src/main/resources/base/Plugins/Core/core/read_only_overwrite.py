"""Confirm replacement of read-only local files on Windows."""
from core.fs.local.read_only import is_read_only
from core.settings import get_setting, SETTINGS_FILE
from fman import ABORT, NO, PLATFORM, YES, YES_TO_ALL
from fman.impl.overwrite_dialog import OverwriteChoice
from fman.url import as_human_readable, basename, splitscheme


SETTING_KEY = 'ask_before_replacing_read_only'
PROMPT_TEXT = '%s is read-only. Do you want to replace it anyway?'


def is_enabled():
	return get_setting(SETTINGS_FILE, SETTING_KEY, True)


class ReadOnlyOverwrite:
	def __init__(self):
		self._replace_all = False

	def confirm(self, operation, dest_url):
		if not self._should_ask(dest_url):
			return dest_url
		answer = operation.show_alert(
			PROMPT_TEXT % basename(dest_url),
			YES | YES_TO_ALL | NO | ABORT, NO
		)
		if answer == YES or answer == YES_TO_ALL:
			if answer == YES_TO_ALL:
				self._replace_all = True
			return dest_url
		if answer == ABORT:
			return OverwriteChoice.ABORT
		return None

	def _should_ask(self, dest_url):
		if PLATFORM != 'Windows' or not is_enabled() or self._replace_all:
			return False
		scheme, _path = splitscheme(dest_url)
		if scheme != 'file://':
			return False
		return is_read_only(as_human_readable(dest_url))
