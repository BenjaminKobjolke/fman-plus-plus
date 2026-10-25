"""Session-only incognito state shared by fman and its plugins."""

ON_INCOGNITO_CHANGED = 'on_incognito_changed'
MARKER_TEXT = 'Incognito'
ON_MESSAGE = 'Incognito on.'
OFF_MESSAGE = 'Incognito off.'

_enabled = False

def is_incognito():
	"""Return whether incognito mode is enabled for this fman session.

	Plugins that record visited folders should skip recording while this is
	True.
	"""
	return _enabled

def set_incognito(enabled):
	global _enabled
	_enabled = enabled
