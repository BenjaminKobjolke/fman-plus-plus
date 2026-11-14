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
from urllib.request import Request, urlopen
import uuid

from build_info import describe_build
from parser import parser as _parser
from process_launch import detached_popen, describe_refused, log_tail
from restart import restart_session
from fixtures import (
	copy_video_fixture, make_deep_folder, make_fixture, make_large_folder,
	parse_core_settings, validate_deep_count, validate_large_count,
	write_core_settings,
)
from dispatch import dispatch
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
	raise RuntimeError(
		'fman did not start; log tail: ' + '\n'.join(log_tail(log_path)))


def _start_fman(session, session_root):
	profile = session['profile']
	environment = os.environ.copy()
	environment['FMAN_DATA_DIRECTORY'] = profile
	environment['PYTHONPATH'] = str(
		Path(__file__).resolve().parents[2] / 'src' / 'main' / 'python'
	)
	main = Path(environment['PYTHONPATH']) / 'fman' / 'main.py'
	log_path = Path(session_root) / 'fman.log'
	with log_path.open('ab') as log:
		process = detached_popen(
			[
				os.environ.get('FMAN_PYTHON', sys.executable), str(main),
				session['left'], session['right'],
			],
			cwd=str(Path(__file__).resolve().parents[2]), env=environment,
			stdout=log, stderr=subprocess.STDOUT,
		)
	session.pop('fman_pid', None)
	session.pop('fman_start_time', None)
	session['pid'] = process.pid
	session['start_time'] = process_start_time(process.pid)
	identity = fman_process_identity(process.pid)
	if identity is not None:
		session['fman_pid'], session['fman_start_time'] = identity
	(Path(session_root) / SESSION_FILE).write_text(
		json.dumps(session, indent=2), encoding='utf-8')
	return _wait_for_state(session, process, log_path)


def _launch(args):
	validate_large_count(args.large)
	validate_deep_count(args.deep)
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
		copy_video_fixture(left, Path(__file__).resolve().parents[2])
	if not args.right:
		make_fixture(right, now)
	if not args.left:
		make_large_folder(left, args.large, now)
		deep = make_deep_folder(left, args.deep)
	else:
		deep = None
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
		'build': describe_build(
			Path(__file__).resolve().parents[2],
			os.environ.get('FMAN_PYTHON', sys.executable),
		).to_dict(),
	}
	if deep is not None:
		session['deep'] = str(deep)
	try:
		_start_fman(session, session_root)
	except Exception:
		shutil.rmtree(session_root, ignore_errors=True)
		raise
	detached_popen(
		[
			sys.executable,
			str(Path(__file__).with_name('session_reaper.py')),
			str(session_root),
	], stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
		cwd=str(Path(__file__).resolve().parents[2]),
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
	if args.action == 'restart':
		return restart_session(session, _api, _start_fman, _current_path())
	try:
		return dispatch(args, session, _api, _settle)
	except URLError as error:
		if isinstance(error.reason, ConnectionRefusedError):
			raise RuntimeError(describe_refused(session)) from error
		raise


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
