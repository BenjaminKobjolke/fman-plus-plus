"""Input safety fences for validation task #2227's isolated desktop session."""

import ntpath
import os
import posixpath
import re
from pathlib import Path

FENCED_ACTIONS = frozenset(('keys', 'type', 'click', 'drag', 'command'))
PROGRESS_DIALOG_TYPE = 'QProgressDialog'
_WINDOWS_DRIVE = re.compile(r'^[A-Za-z]:')


def fence_roots(session):
	return [
		Path(session['profile']).parent,
		Path(session['left']),
		Path(session['right']),
	]


def _normalized_path(path):
	path = os.fspath(path).replace('\\', '/')
	if _WINDOWS_DRIVE.match(path):
		return ntpath.normpath(path.replace('/', '\\')).casefold(), True
	return posixpath.normpath(path).casefold(), False


def is_inside(url, roots):
	if not isinstance(url, str) or '://' not in url:
		return False
	path = url.split('://', 1)[1]
	if path.startswith('/') and _WINDOWS_DRIVE.match(path[1:]):
		path = path[1:]
	if not path:
		return False
	path, windows_path = _normalized_path(path)
	for root in roots:
		root = os.fspath(root)
		if not root:
			continue
		normalized_root, windows_root = _normalized_path(root)
		if windows_path != windows_root:
			continue
		try:
			common = (ntpath.commonpath((normalized_root, path))
				if windows_path else posixpath.commonpath((normalized_root, path)))
		except ValueError:
			continue
		if common == normalized_root:
			return True
	return False


def check_inside_fixtures(state, roots):
	panes = state.get('panes') if isinstance(state, dict) else None
	if not isinstance(panes, list) or not panes:
		raise RuntimeError('State response contains no panes.')
	for index, pane in enumerate(panes):
		if not isinstance(pane, dict):
			raise RuntimeError('State response contains malformed pane %d.' % index)
		path = pane.get('path')
		if not is_inside(path, roots):
			raise RuntimeError(
				'Pane %d path %r is outside the session fixtures.' % (index, path))


def check_no_open_dialog(dialog):
	if dialog is None or dialog.get('type') == PROGRESS_DIALOG_TYPE:
		return
	raise RuntimeError(
		'Cannot run a command while %s is open (%s). Answer it with '
		'keys Return or keys Escape.' % (
			dialog.get('type', 'a dialog'), dialog.get('text', '')))


def guard_input(session, args, api):
	if args.action not in FENCED_ACTIONS:
		return None
	if args.action == 'keys' and getattr(args, 'chords', None) == ['Escape']:
		return None
	state = api(session, 'GET', '/v1/state')
	check_inside_fixtures(state, fence_roots(session))
	if args.action == 'command':
		dialog = api(session, 'GET', '/v1/dialog').get('dialog')
		check_no_open_dialog(dialog)
	return state
