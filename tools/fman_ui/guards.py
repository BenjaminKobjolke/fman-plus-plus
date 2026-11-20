"""Input safety fences for validation task #2227's isolated desktop session."""

import ntpath
import os
import posixpath
import re
from pathlib import Path
from typing import Mapping, Sequence

FENCED_ACTIONS = frozenset((
	'keys', 'type', 'click', 'drag', 'drop', 'command'))
PROGRESS_DIALOG_TYPE = 'QProgressDialog'
NON_MODAL_DIALOG_TYPES = frozenset((PROGRESS_DIALOG_TYPE, 'Overlay'))
_WINDOWS_DRIVE = re.compile(r'^[A-Za-z]:')
DRIVE_OVERVIEW_COMMANDS = frozenset((
	'move_cursor_up', 'move_cursor_down', 'move_cursor_home',
	'move_cursor_end', 'show_explorer_properties', 'go_back',
))
DRIVE_OVERVIEW_KEYS = frozenset(('Up', 'Down', 'Home', 'End'))


def fence_roots(session):
	roots = [
		Path(session['profile']).parent,
		Path(session['left']),
		Path(session['right']),
	]
	if session.get('network_share_unc'):
		roots.append(session['network_share_unc'])
	remote_paths = session.get('remote_paths')
	if isinstance(remote_paths, dict):
		roots.extend(path for path in remote_paths.values()
			if isinstance(path, str) and path)
	return roots


def guard_drop_sources(session: Mapping[str, str], files: Sequence[str]) -> list[str]:
	root = Path(session['profile']).parent.resolve()
	resolved_files = []
	for file in files:
		try:
			path = Path(file).resolve(strict=True)
		except (OSError, RuntimeError, TypeError):
			raise RuntimeError(
				'Drop sources must be existing files inside the session.')
		if not path.is_file() or not is_inside(path.as_uri(), [root]):
			raise RuntimeError(
				'Drop sources must be existing files inside the session.')
		resolved_files.append(str(path))
	return resolved_files


def _normalized_path(path):
	path = os.fspath(path).replace('\\', '/')
	if _WINDOWS_DRIVE.match(path):
		return ntpath.normpath(path.replace('/', '\\')).casefold(), True
	if path.startswith('//'):
		return ntpath.normpath(path.replace('/', '\\')).casefold(), True
	return posixpath.normpath(path).casefold(), False


def _is_inside_url_root(url, root):
	url_scheme, url_path = url.split('://', 1)
	root_scheme, root_path = root.split('://', 1)
	if url_scheme.casefold() != root_scheme.casefold():
		return False
	url_path = url_path.rstrip('/')
	root_path = root_path.rstrip('/')
	if not url_path or not root_path:
		return False
	url_path = posixpath.normpath(url_path).casefold()
	root_path = posixpath.normpath(root_path).casefold()
	try:
		return posixpath.commonpath((root_path, url_path)) == root_path
	except ValueError:
		return False


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
		if '://' in root:
			if _is_inside_url_root(url, root):
				return True
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


def check_inside_fixtures(state, roots, args=None):
	panes = state.get('panes') if isinstance(state, dict) else None
	if not isinstance(panes, list) or not panes:
		raise RuntimeError('State response contains no panes.')
	for index, pane in enumerate(panes):
		if not isinstance(pane, dict):
			raise RuntimeError('State response contains malformed pane %d.' % index)
		path = pane.get('path')
		if path == 'drives://' and args is not None and _overview_action_allowed(args):
			continue
		if not is_inside(path, roots):
			if path == 'drives://' and args is not None:
				raise RuntimeError(
					'Drive overview allows only command %s or keys %s.' % (
						', '.join(sorted(DRIVE_OVERVIEW_COMMANDS)),
						', '.join(sorted(DRIVE_OVERVIEW_KEYS))))
			raise RuntimeError(
				'Pane %d path %r is outside the session fixtures.' % (index, path))


def _overview_action_allowed(args):
	if args.action == 'command':
		return getattr(args, 'name', None) in DRIVE_OVERVIEW_COMMANDS
	if args.action == 'keys':
		chords = getattr(args, 'chords', None)
		return bool(chords) and all(key in DRIVE_OVERVIEW_KEYS for key in chords)
	return False


def check_no_open_dialog(dialog):
	if dialog is None or dialog.get('type') in NON_MODAL_DIALOG_TYPES:
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
	check_inside_fixtures(state, fence_roots(session), args)
	if args.action == 'command':
		dialog = api(session, 'GET', '/v1/dialog').get('dialog')
		check_no_open_dialog(dialog)
	return state
