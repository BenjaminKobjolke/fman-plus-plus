"""Read the app-level scroll margin setting."""

SCROLL_MARGIN_SETTING = 'scroll_margin'
DEFAULT_SCROLL_MARGIN = 0


def load_scroll_margin(settings) -> int:
	value = settings.get(SCROLL_MARGIN_SETTING, DEFAULT_SCROLL_MARGIN)
	# Settings.json is hand-edited, so a bad value should not break startup.
	if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
		return value
	return DEFAULT_SCROLL_MARGIN
