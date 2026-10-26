"""Command line driver for an isolated fman UI automation session."""

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid

from recycle_cleanup import cleanup_session as cleanup_recycle_bin


def _root():
	return Path(os.environ.get('TEMP', Path.home())) / 'fman-ui'


def _current_path():
	return _root() / 'current.json'


def _read_current():
	return json.loads(_current_path().read_text(encoding='utf-8'))


def _api(session, method, path, payload=None):
	token = Path(session['token_path']).read_text(encoding='utf-8').strip()
	data = None if payload is None else json.dumps(payload).encode('utf-8')
	request = Request(
		'http://127.0.0.1:%d%s' % (session['port'], path), data=data,
		headers={'Authorization': 'Bearer ' + token}, method=method,
	)
	try:
		with urlopen(request, timeout=3) as response:
			if response.headers.get_content_type() == 'image/png':
				return response.read()
			return json.loads(response.read().decode('utf-8'))
	except HTTPError as error:
		try:
			message = json.loads(error.read().decode('utf-8')).get('error')
		except (ValueError, AttributeError):
			message = str(error)
		raise RuntimeError(message or str(error)) from error


def _reserve_port():
	with socket.socket() as listener:
		listener.bind(('127.0.0.1', 0))
		return listener.getsockname()[1]


def _make_fixture(path):
	path.mkdir(parents=True, exist_ok=True)
	(path / 'visible.txt').write_text('visible fixture\n', encoding='utf-8')
	hidden = path / 'hidden.txt'
	hidden.write_text('hidden fixture\n', encoding='utf-8')
	(path / 'folder').mkdir(exist_ok=True)
	bracket_folder = path / '[--brackets--]'
	bracket_folder.mkdir(exist_ok=True)
	(bracket_folder / 'visible.txt').write_text(
		'visible fixture in a bracketed folder\n', encoding='utf-8')
	if os.name == 'nt':
		subprocess.run(['attrib', '+h', str(hidden)], check=True,
			stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _wait_for_state(session, process, log_path):
	deadline = time.monotonic() + 60
	while time.monotonic() < deadline:
		try:
			return _api(session, 'GET', '/v1/state')
		except (OSError, RuntimeError, URLError):
			if process.poll() is not None:
				break
			time.sleep(.25)
	if process.poll() is None:
		process.kill()
	try:
		tail = log_path.read_text(encoding='utf-8', errors='replace').splitlines()[-40:]
	except OSError:
		tail = []
	raise RuntimeError('fman did not start; log tail: ' + '\n'.join(tail))


def _launch(args):
	root = _root()
	root.mkdir(parents=True, exist_ok=True)
	session_id = uuid.uuid4().hex
	session_root = root / session_id
	profile = session_root / 'profile'
	left = Path(args.left).resolve() if args.left else session_root / 'left'
	right = Path(args.right).resolve() if args.right else session_root / 'right'
	if not args.left:
		_make_fixture(left)
	if not args.right:
		_make_fixture(right)
	local = profile / 'Local'
	local.mkdir(parents=True, exist_ok=True)
	port = _reserve_port()
	settings = {'single_instance': False, 'scripting_api': {
		'enabled': True, 'automation': True, 'port': port,
		'command_access': 'all', 'allowed_hosts': [],
	}}
	settings_path = local / 'Settings.json'
	settings_path.write_text(json.dumps(settings, indent=2), encoding='utf-8')
	# A non-empty session file suppresses first-run onboarding and starts with
	# two deterministic panes, one for each supplied or generated fixture.
	(local / 'Session.json').write_text(json.dumps({
		'panes': [{}, {}],
	}, indent=2), encoding='utf-8')
	token_path = local / 'ScriptingApiToken.txt'
	token_path.write_text(uuid.uuid4().hex, encoding='utf-8')
	session = {
		'session_id': session_id, 'pid': None, 'port': port,
		'token_path': str(token_path), 'profile': str(profile),
		'left': str(left), 'right': str(right),
	}
	log_path = session_root / 'fman.log'
	environment = os.environ.copy()
	environment['FMAN_DATA_DIRECTORY'] = str(profile)
	environment['PYTHONPATH'] = str(
		Path(__file__).resolve().parents[2] / 'src' / 'main' / 'python'
	)
	main = Path(environment['PYTHONPATH']) / 'fman' / 'main.py'
	flags = (
		getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
		| getattr(subprocess, 'DETACHED_PROCESS', 0)
	)
	with log_path.open('wb') as log:
		process = subprocess.Popen(
			[
				os.environ.get('FMAN_PYTHON', sys.executable), str(main),
				str(left), str(right),
			],
			cwd=str(Path(__file__).resolve().parents[2]), env=environment,
			stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
		)
	session['pid'] = process.pid
	try:
		_wait_for_state(session, process, log_path)
	except Exception:
		shutil.rmtree(session_root, ignore_errors=True)
		raise
	_current_path().write_text(json.dumps(session, indent=2), encoding='utf-8')
	return session


def _settle(milliseconds):
	if milliseconds:
		time.sleep(milliseconds / 1000)


def _run(args):
	if args.action == 'launch':
		return _launch(args)
	session = _read_current()
	if args.action == 'close':
		subprocess.run(['taskkill', '/PID', str(session['pid']), '/T', '/F'],
			check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		try:
			removed_entries = cleanup_recycle_bin(
				Path(session['profile']).parent)
		except OSError:
			removed_entries = 0
		shutil.rmtree(Path(session['profile']).parent, ignore_errors=True)
		_current_path().unlink(missing_ok=True)
		return {'ok': True, 'recycle_bin_entries_removed': removed_entries}
	if args.action in ('state', 'commands'):
		return _api(session, 'GET', '/v1/' + args.action)
	if args.action == 'files':
		return _api(session, 'GET', '/v1/files?pane=%d' % args.pane)
	if args.action == 'dialog':
		return _api(session, 'GET', '/v1/dialog')
	if args.action == 'command':
		payload = {
			'name': args.name, 'args': json.loads(args.args_json),
			'pane': args.pane,
		}
		try:
			result = _api(session, 'POST', '/v1/command', payload)
		except (TimeoutError, URLError) as error:
			if isinstance(error, URLError) and not isinstance(
					error.reason, TimeoutError):
				raise
			try:
				dialog = _api(session, 'GET', '/v1/dialog').get('dialog')
			except (OSError, RuntimeError, URLError):
				raise error
			if dialog is None:
				raise error
			return {'running': True, 'dialog': dialog}
		_settle(args.settle)
		return result
	if args.action == 'keys':
		result = _api(session, 'POST', '/v1/keys', {'keys': args.chords})
		_settle(args.settle)
		return result
	if args.action == 'type':
		result = _api(session, 'POST', '/v1/keys', {'text': args.text})
		_settle(args.settle)
		return result
	if args.action == 'click':
		if args.file is not None:
			state = _api(session, 'GET', '/v1/state')
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
		result = _api(session, 'POST', '/v1/click', payload)
		_settle(args.settle)
		return result
	if args.action == 'screenshot':
		data = _api(session, 'GET', '/v1/screenshot')
		Path(args.png_path).write_bytes(data)
		return {'path': str(Path(args.png_path).resolve())}
	raise RuntimeError('Unknown command.')


def _parser():
	parser = argparse.ArgumentParser(prog='fman_ui')
	commands = parser.add_subparsers(dest='action', required=True)
	launch = commands.add_parser('launch')
	launch.add_argument('--left')
	launch.add_argument('--right')
	for name in ('state', 'commands', 'close', 'dialog'):
		commands.add_parser(name)
	command = commands.add_parser('command')
	command.add_argument('name')
	command.add_argument('args_json', nargs='?', default='{}')
	command.add_argument('--pane', type=int, default=0)
	command.add_argument('--settle', type=int, default=500)
	files = commands.add_parser('files')
	files.add_argument('--pane', type=int, default=0)
	keys = commands.add_parser('keys')
	keys.add_argument('chords', nargs='+')
	keys.add_argument('--settle', type=int, default=500)
	type_text = commands.add_parser('type')
	type_text.add_argument('text')
	type_text.add_argument('--settle', type=int, default=500)
	click = commands.add_parser('click')
	choice = click.add_mutually_exclusive_group(required=True)
	choice.add_argument('--file')
	choice.add_argument('--x', type=int)
	click.add_argument('--y', type=int)
	click.add_argument('--pane', type=int, default=0)
	click.add_argument('--right', action='store_true')
	click.add_argument('--double', action='store_true')
	click.add_argument('--settle', type=int, default=500)
	screenshot = commands.add_parser('screenshot')
	screenshot.add_argument('png_path')
	return parser


def main(argv=None):
	try:
		args = _parser().parse_args(argv)
		result = _run(args)
		print(json.dumps(result))
		return 0
	except (OSError, ValueError, RuntimeError, URLError) as error:
		print(json.dumps({'error': str(error)}))
		return 1


if __name__ == '__main__':
	sys.exit(main())
