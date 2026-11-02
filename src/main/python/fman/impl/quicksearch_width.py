QUICKSEARCH_WIDTH_SETTING = 'quicksearch_width'


class QuicksearchWidth:
	def __init__(self, settings):
		self._settings = settings

	def get(self) -> int | None:
		return self._settings.get(QUICKSEARCH_WIDTH_SETTING, None)

	def save(self, width: int, default_width: int) -> None:
		if width <= default_width:
			self._settings.pop(QUICKSEARCH_WIDTH_SETTING)
		else:
			self._settings[QUICKSEARCH_WIDTH_SETTING] = width
		self._settings.flush()
