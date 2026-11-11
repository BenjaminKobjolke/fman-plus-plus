"""Command line driver for an isolated fman UI automation session."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid

from parser import parser as _parser
from fixtures import (
	make_fixture, make_large_folder, parse_core_settings,
	validate_large_count, write_core_settings,
)
from session_reaper import (
	SESSION_FILE, close_session, fman_process_identity, kill_process,
	process_start_time, reap_stale,
)


def _root():
	return Path(os.environ.get('TEMP') or tempfile.gettempdir()) / 'fman-ui'


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


def _detached_flags():
	return (
		getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
		| getattr(subprocess, 'DETACHED_PROCESS', 0)
	)


def _wait_for_state(session, process, log_path):
	deadline = time.monotonic() + 60
	while time.monotonic() < deadline:
		identity = fman_process_identity(process.pid)
		if identity is not None and identity != (
				session.get('fman_pid'), session.get('fman_start_time')):
			session['fman_pid'], session['fman_start_time'] = identity
			Path(session['profile']).parent.joinpath(SESSION_FILE).write_text(
				json.dumps(session, indent=2), encoding='utf-8')
		try:
			return _api(session, 'GET', '/v1/state')
		except (OSError, RuntimeError, URLError):
			if process.poll() is not None:
				break
			time.sleep(.25)
	if process.poll() is None:
		kill_process(session.get('fman_pid', process.pid),
			session.get('fman_start_time', session['start_time']))
	try:
		tail = log_path.read_text(encoding='utf-8', errors='replace').splitlines()[-40:]
	except OSError:
		tail = []
	raise RuntimeError('fman did not start; log tail: ' + '\n'.join(tail))


def _launch(args):
	validate_large_count(args.large)
	core_settings = parse_core_settings(args.core_settings)
	now = time.time()
	root = _root()
	root.mkdir(parents=True, exist_ok=True)
	reap_stale(root, now)
	session_id = uuid.uuid4().hex
	session_root = root / session_id
	profile = session_root / 'profile'
	left = Path(args.left).resolve() if args.left else session_root / 'left'
	right = Path(args.right).resolve() if args.right else session_root / 'right'
	if not args.left:
		make_fixture(left, now)
	if not args.right:
		make_fixture(right, now)
	if not args.left:
		make_large_folder(left, args.large, now)
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
	write_core_settings(profile, core_settings)
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
	with log_path.open('wb') as log:
		process = subprocess.Popen(
			[
				os.environ.get('FMAN_PYTHON', sys.executable), str(main),
				str(left), str(right),
			],
			cwd=str(Path(__file__).resolve().parents[2]), env=environment,
			stdout=log, stderr=subprocess.STDOUT,
			creationflags=_detached_flags(),
			start_new_session=os.name != 'nt',
		)
	session['pid'] = process.pid
	session['start_time'] = process_start_time(process.pid)
	identity = fman_process_identity(process.pid)
	if identity is not None:
		session['fman_pid'], session['fman_start_time'] = identity
	(session_root / SESSION_FILE).write_text(
		json.dumps(session, indent=2), encoding='utf-8')
	try:
		_wait_for_state(session, process, log_path)
	except Exception:
		shutil.rmtree(session_root, ignore_errors=True)
		raise
	subprocess.Popen(
		[
			sys.executable,
			str(Path(__file__).with_name('session_reaper.py')),
			str(session_root),
		], creationflags=_detached_flags(), stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
		cwd=str(Path(__file__).resolve().parents[2]),
		start_new_session=os.name != 'nt',
	)
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
		session_root = Path(session['profile']).parent
		if 'start_time' not in session:
			subprocess.run(['taskkill', '/PID', str(session['pid']), '/T', '/F'],
				check=False, stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL)
		removed_entries = close_session(session_root)
		_current_path().unlink(missing_ok=True)
		return {'ok': True, 'recycle_bin_entries_removed': removed_entries}
	profile = session.get('profile')
	if profile is not None:
		session_file = Path(profile).parent / SESSION_FILE
		if session_file.exists():
			os.utime(session_file, None)
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
	if args.action == 'drag':
		payload = {
			'x': args.x, 'y': args.y, 'to_x': args.to_x, 'to_y': args.to_y,
		}
		result = _api(session, 'POST', '/v1/drag', payload)
		_settle(args.settle)
		return result
	if args.action == 'screenshot':
		data = _api(session, 'GET', '/v1/screenshot')
		Path(args.png_path).write_bytes(data)
		return {'path': str(Path(args.png_path).resolve())}
	raise RuntimeError('Unknown command.')


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
