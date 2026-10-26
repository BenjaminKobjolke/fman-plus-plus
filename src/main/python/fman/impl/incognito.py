"""Session-only incognito state and pane snapshots shared by fman and plugins."""

from collections import namedtuple

ON_INCOGNITO_CHANGED = 'on_incognito_changed'
MARKER_TEXT = 'Incognito'
ON_MESSAGE = 'Incognito on.'
OFF_MESSAGE = 'Incognito off.'

_enabled = False
PaneState = namedtuple('PaneState', ('location', 'file_under_cursor'))
_pane_states = ()

def is_incognito():
	"""Return whether incognito mode is enabled for this fman session.

	Plugins that record visited folders should skip recording while this is
	True.
	"""
	return _enabled

def set_incognito(enabled):
	global _enabled, _pane_states
	_enabled = enabled
	if not enabled:
		_pane_states = ()

def remember_pane_states(states):
	global _pane_states
	_pane_states = tuple(states)

def get_pane_states():
	return _pane_states

def restore_pane_states(panes, states):
	for pane, state in zip(panes, states):
		def callback(pane=pane, file_under_cursor=state.file_under_cursor):
			if file_under_cursor is not None:
				try:
					pane.place_cursor_at(file_under_cursor)
				except ValueError:
					pass
		pane.set_path(state.location, callback)
