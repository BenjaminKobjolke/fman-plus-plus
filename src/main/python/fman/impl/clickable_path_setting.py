"""Persist and apply whether parent folders in the location bar are clickable."""

CLICKABLE_PATH_SETTING = 'clickable_path'
CLICKABLE_PATH_ON_MESSAGE = 'Clickable path on.'
CLICKABLE_PATH_OFF_MESSAGE = 'Clickable path off.'


class ClickablePathSetting:
	def __init__(self, settings):
		self._settings = settings

	def is_enabled(self):
		return self._settings.get(CLICKABLE_PATH_SETTING, True) is not False

	def apply(self, window):
		window.set_clickable_path(self.is_enabled())

	def toggle(self, window):
		enabled = not self.is_enabled()
		if enabled:
			self._settings.pop(CLICKABLE_PATH_SETTING)
			message = CLICKABLE_PATH_ON_MESSAGE
		else:
			self._settings[CLICKABLE_PATH_SETTING] = False
			message = CLICKABLE_PATH_OFF_MESSAGE
		self._settings.flush()
		self.apply(window)
		return message
