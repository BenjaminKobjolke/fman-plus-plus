"""Dispatch commands that operate on an active UI automation session."""

import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit

from guards import guard_input
from session_reaper import SESSION_FILE
from window_size import capture_screenshot, png_size


def dispatch(args, session, api, settle):
	profile = session.get('profile')
	if profile is not None:
		session_file = Path(profile).parent / SESSION_FILE
		if session_file.exists():
			os.utime(session_file, None)
	state = guard_input(session, args, api)
	if args.action in ('state', 'commands'):
		return api(session, 'GET', '/v1/' + args.action)
	if args.action == 'files':
		return api(session, 'GET', '/v1/files?pane=%d' % args.pane)
	if args.action == 'dialog':
		return api(session, 'GET', '/v1/dialog')
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
			pane_index = args.pane
			if pane_index < 0 or pane_index >= len(state['panes']):
				raise RuntimeError('Pane index is out of range.')
			if not urlsplit(args.file).scheme:
				base = state['panes'][pane_index]['path'].rstrip('/') + '/'
				file_url = base + args.file
			else:
				file_url = args.file
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
	if args.action == 'screenshot':
		data = capture_screenshot(session, api)
		Path(args.png_path).write_bytes(data)
		width, height = png_size(data)
		return {
			'path': str(Path(args.png_path).resolve()),
			'width': width, 'height': height,
		}
	raise RuntimeError('Unknown command.')
