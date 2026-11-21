"""Dispatch commands that operate on an active UI automation session."""

import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit

from guards import guard_drop_sources, guard_input
from session_reaper import SESSION_FILE
from window_size import capture_screenshot, png_size


def dispatch(args, session, api, settle):
	profile = session.get('profile')
	if profile is not None:
		session_file = Path(profile).parent / SESSION_FILE
		if session_file.exists():
			os.utime(session_file, None)
	unfenced = args.action in (
		'window', 'native-windows', 'close-native-windows',
	)
	state = None if unfenced else guard_input(session, args, api)
	if args.action in ('state', 'commands'):
		return api(session, 'GET', '/v1/' + args.action)
	if args.action == 'files':
		return api(session, 'GET', '/v1/files?pane=%d' % args.pane)
	if args.action == 'dialog':
		return api(session, 'GET', '/v1/dialog')
	if args.action == 'links':
		return api(session, 'GET', '/v1/links')
	if args.action == 'native-windows':
		return api(session, 'GET', '/v1/native-windows')
	if args.action == 'close-native-windows':
		return api(session, 'POST', '/v1/native-windows/close', {})
	if args.action == 'viewer':
		return api(session, 'GET', '/v1/viewer?pane=%d' % args.pane)
	if args.action == 'command':
		payload = {
			'name': args.name, 'args': json.loads(args.args_json),
			'pane': args.pane,
		}
		try:
			result = api(session, 'POST', '/v1/command', payload)
		except (TimeoutError, URLError) as error:
			if isinstance(error, URLError) and not isinstance(
					error.reason, TimeoutError):
				raise
			try:
				dialog = api(session, 'GET', '/v1/dialog').get('dialog')
			except (OSError, RuntimeError, URLError):
				raise error
			if dialog is None:
				raise error
			return {'running': True, 'dialog': dialog}
		settle(args.settle)
		return result
	if args.action == 'keys':
		result = api(session, 'POST', '/v1/keys', {'keys': args.chords})
		settle(args.settle)
		return result
	if args.action == 'type':
		result = api(session, 'POST', '/v1/keys', {'text': args.text})
		settle(args.settle)
		return result
	if args.action == 'click':
		if args.file is not None:
			pane_index, file_url = _resolve_file_url(
				state, args.pane, args.file)
			payload = {'pane': pane_index, 'file': file_url}
		else:
			if args.y is None:
				raise RuntimeError('Both --x and --y are required.')
			payload = {'x': args.x, 'y': args.y}
		payload.update({
			'button': 'right' if args.right else 'left', 'double': args.double,
		})
		result = api(session, 'POST', '/v1/click', payload)
		settle(args.settle)
		return result
	if args.action == 'drag':
		payload = {
			'x': args.x, 'y': args.y, 'to_x': args.to_x, 'to_y': args.to_y,
		}
		result = api(session, 'POST', '/v1/drag', payload)
		settle(args.settle)
		return result
	if args.action == 'drop':
		action = 'default'
		if args.copy:
			action = 'copy'
		elif args.move:
			action = 'move'
		payload = {
			'pane': args.pane,
			'files': guard_drop_sources(session, args.file),
			'onto': args.onto,
			'action': action,
		}
		result = api(session, 'POST', '/v1/drop', payload)
		settle(args.settle)
		return result
	if args.action == 'drag-file':
		source_pane = args.pane
		_pane_path(state, args.to_pane)
		files = [
			_resolve_file_url(state, source_pane, file_name)[1]
			for file_name in args.file
		]
		onto = None
		if args.onto is not None:
			onto = _resolve_file_url(state, args.to_pane, args.onto)[1]
		action = 'default'
		if args.copy:
			action = 'copy'
		elif args.move:
			action = 'move'
		result = api(session, 'POST', '/v1/drag-files', {
			'source_pane': source_pane,
			'files': files,
			'pane': args.to_pane,
			'onto': onto,
			'action': action,
		})
		settle(args.settle)
		return result
	if args.action == 'hover':
		result = api(session, 'POST', '/v1/hover', {
			'x': args.x, 'y': args.y,
		})
		settle(args.settle)
		return result
	if args.action == 'window':
		screen = getattr(args, 'screen', None)
		x = getattr(args, 'x', None)
		y = getattr(args, 'y', None)
		if screen is not None and (x is not None or y is not None):
			raise RuntimeError('--screen cannot be combined with --x or --y.')
		payload = {'width': args.width, 'height': args.height}
		payload.update({key: value for key, value in (
			('x', x), ('y', y), ('screen', screen),
		) if value is not None})
		result = api(session, 'POST', '/v1/window', payload)
		session['requested_window'] = {
			'width': args.width, 'height': args.height,
		}
		session['window'] = result
		session_file = Path(session['profile']).parent / SESSION_FILE
		session_data = json.dumps(session, indent=2)
		session_file.write_text(session_data, encoding='utf-8')
		current_file = session_file.parent.parent / 'current.json'
		current_file.write_text(session_data, encoding='utf-8')
		return result
	if args.action == 'screenshot':
		data = capture_screenshot(
			session, api, screen=getattr(args, 'screen', None))
		Path(args.png_path).write_bytes(data)
		width, height = png_size(data)
		return {
			'path': str(Path(args.png_path).resolve()),
			'width': width, 'height': height,
		}
	raise RuntimeError('Unknown command.')


def _resolve_file_url(state, pane_index, file_name):
	base = _pane_path(state, pane_index).rstrip('/') + '/'
	if not urlsplit(file_name).scheme:
		file_name = base + file_name
	return pane_index, file_name


def _pane_path(state, pane_index):
	if pane_index < 0 or pane_index >= len(state['panes']):
		raise RuntimeError('Pane index is out of range.')
	return state['panes'][pane_index]['path']
