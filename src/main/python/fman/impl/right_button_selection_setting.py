"""Persist and apply the right-button selection mode."""

RIGHT_BUTTON_SELECTION_SETTING = 'right_button_selection'
RIGHT_BUTTON_SELECTION_ON_MESSAGE = (
	'Right-button selection on. Hold the right button for the context menu.'
)
RIGHT_BUTTON_SELECTION_OFF_MESSAGE = 'Right-button selection off.'


class RightButtonSelectionSetting:
	def __init__(self, settings):
		self._settings = settings

	def is_enabled(self):
		return self._settings.get(RIGHT_BUTTON_SELECTION_SETTING, False) is True

	def apply(self, window):
		window.set_right_button_selection(self.is_enabled())

	def toggle(self, window):
		if self.is_enabled():
			self._settings.pop(RIGHT_BUTTON_SELECTION_SETTING)
			message = RIGHT_BUTTON_SELECTION_OFF_MESSAGE
		else:
			self._settings[RIGHT_BUTTON_SELECTION_SETTING] = True
			message = RIGHT_BUTTON_SELECTION_ON_MESSAGE
		self._settings.flush()
		self.apply(window)
		return message
