"""Run an isolated per-user fman installer update check."""

import json
import os
from pathlib import Path
import psutil
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from fixtures import make_fixture
from installer_snapshot import (
	FMAN_KEY, UserInstallSnapshot, WindowsUserRegistry,
	restore_snapshot, take_snapshot,
)
from installer_processes import (
	fman_processes as processes_in_app, kill_app_processes,
	process_is_running, terminate,
)
from native_dialogs import (
	click_dialog_button, close_window as close_native_window,
	dialogs_for_process, read_file_version, windows_for_pids,
)
from process_launch import detached_popen


SESSION_ROOT = (
	Path(os.environ.get('TEMP') or tempfile.gettempdir()) / 'fman-ui' / 'installer'
)
SESSION_FILE = SESSION_ROOT / 'installer.json'
SENTINEL_NAME = 'fman_ui_installer_sentinel.txt'
SETUP_TIMEOUT_SECONDS = 300
WINDOW_TIMEOUT_SECONDS = 60
registry = None


def _registry():
	return registry or WindowsUserRegistry()


def _repo_root():
	return Path(__file__).resolve().parents[2]


def _setup_path(setup=None):
	path = Path(setup) if setup else _repo_root() / 'target' / 'fmanSetup.exe'
	return path.resolve()


def setup_command(setup, install_dir):
	return [str(setup), '/S', '/CurrentUser', '/D=' + str(install_dir)]


def setup_environment(environment=None):
	result = dict(os.environ if environment is None else environment)
	result['__COMPAT_LAYER'] = 'RunAsInvoker'
	return result


def _load_session():
	try:
		return json.loads(SESSION_FILE.read_text(encoding='utf-8'))
	except FileNotFoundError as error:
		raise RuntimeError('No installer session is active.') from error


def _save_session(session):
	SESSION_ROOT.mkdir(parents=True, exist_ok=True)
	SESSION_FILE.write_text(json.dumps(session, indent=2), encoding='utf-8')


def prepare_profile(app_dir):
	app_dir = Path(app_dir)
	(app_dir / 'portable.txt').write_text('', encoding='utf-8')
	local = app_dir / 'Data' / 'Local'
	local.mkdir(parents=True, exist_ok=True)
	(local / 'Settings.json').write_text(json.dumps({
		'single_instance': False, 'error_reports': False,
		'usage_metrics': False,
	}, indent=2), encoding='utf-8')
	(local / 'Session.json').write_text(json.dumps({'panes': [{}, {}]}, indent=2),
		encoding='utf-8')
	sentinel = app_dir / 'Plugins' / 'Core' / SENTINEL_NAME
	sentinel.parent.mkdir(parents=True, exist_ok=True)
	sentinel.write_text('throwaway installer sentinel\n', encoding='utf-8')
	return sentinel


def _wait_for_windows(pid, deadline):
	while time.monotonic() < deadline:
		windows = windows_for_pids({pid})
		if windows:
			return windows
		if not process_is_running(pid):
			break
		time.sleep(.25)
	raise RuntimeError('fman process %s did not open a visible window.' % pid)


def launch(setup=None, windows=2):
	if os.name != 'nt':
		raise RuntimeError('The installer session is available only on Windows.')
	if SESSION_FILE.exists():
		cleanup()
	setup = _setup_path(setup)
	if not setup.is_file():
		raise FileNotFoundError('Windows installer does not exist: %s' % setup)
	user_registry = _registry()
	if user_registry.key_exists(FMAN_KEY):
		raise RuntimeError(
			'Refusing installer check because HKCU\\Software\\fman already exists.')
	if not 1 <= windows <= 4:
		raise ValueError('--windows must be between 1 and 4.')
	install_id = uuid.uuid4().hex
	session_dir = SESSION_ROOT / install_id
	install_dir = session_dir / 'app'
	snapshot = take_snapshot(user_registry)
	session = {
		'session_dir': str(session_dir), 'install_dir': str(install_dir),
		'setup': str(setup), 'snapshot': snapshot.to_dict(),
		'windows': [], 'setup_pid': None, 'waiter_pid': None,
		'update_started_at': None,
	}
	_save_session(session)
	try:
		session_dir.mkdir(parents=True, exist_ok=True)
		left, right = session_dir / 'left', session_dir / 'right'
		make_fixture(left, time.time())
		make_fixture(right, time.time())
		result = subprocess.run(
			setup_command(setup, install_dir), env=setup_environment(),
			timeout=SETUP_TIMEOUT_SECONDS, check=False)
		if result.returncode != 0:
			raise RuntimeError(
				'Initial installer exited with code %s.' % result.returncode)
		sentinel = prepare_profile(install_dir)
		exe = install_dir / 'fman.exe'
		deadline = time.monotonic() + WINDOW_TIMEOUT_SECONDS
		for _ in range(windows):
			process = detached_popen(
				[str(exe), '--new-instance', str(left), str(right)],
				cwd=str(install_dir))
			created = psutil.Process(process.pid).create_time()
			opened = _wait_for_windows(process.pid, deadline)
			session['windows'].append({
				'pid': process.pid, 'create_time': created,
				'title': opened[0].title,
			})
			_save_session(session)
		return {
			'install_dir': str(install_dir), 'version': read_file_version(exe),
			'sentinel_present': sentinel.is_file(), 'windows': session['windows'],
		}
	except Exception:
		cleanup()
		raise


def _close_first_window(session):
	if not session['windows']:
		return
	first = session['windows'][0]
	for window in windows_for_pids({first['pid']}):
		close_native_window(window.hwnd)
	deadline = time.monotonic() + 15
	while time.monotonic() < deadline and process_is_running(first['pid']):
		time.sleep(.25)
	if process_is_running(first['pid']):
		raise RuntimeError('The first fman window did not close within 15 seconds.')


def update():
	session = _load_session()
	_close_first_window(session)
	session['update_started_at'] = time.time()
	exit_path = Path(session['session_dir']) / 'installer_exit.json'
	exit_path.unlink(missing_ok=True)
	waiter = Path(__file__).with_name('installer_waiter.py')
	process = detached_popen([
		sys.executable, str(waiter), session['session_dir'],
		session['setup'], session['install_dir'],
	], cwd=str(_repo_root()))
	session['waiter_pid'] = process.pid
	session['waiter_create_time'] = psutil.Process(process.pid).create_time()
	_save_session(session)
	return {
		'waiter_pid': process.pid,
		'update_started_at': session['update_started_at'],
	}


def _discover_setup_pid(session):
	if session.get('setup_pid') or not session.get('waiter_pid'):
		return
	try:
		waiter = psutil.Process(session['waiter_pid'])
		children = waiter.children()
		setup_path = os.path.normcase(os.path.abspath(session['setup']))
		for child in children:
			try:
				if os.path.normcase(os.path.abspath(child.exe())) == setup_path:
					session['setup_pid'] = child.pid
					session['setup_create_time'] = child.create_time()
					_save_session(session)
					return
			except (psutil.NoSuchProcess, psutil.AccessDenied):
				continue
	except (psutil.NoSuchProcess, psutil.AccessDenied):
		pass


def _exit_result(session):
	path = Path(session['session_dir']) / 'installer_exit.json'
	try:
		return json.loads(path.read_text(encoding='utf-8'))
	except FileNotFoundError:
		return None


def state():
	session = _load_session()
	_discover_setup_pid(session)
	exit_result = _exit_result(session)
	waiter_running = bool(session.get('waiter_pid')
		and process_is_running(session['waiter_pid']))
	started = session.get('update_started_at')
	setup_pid = session.get('setup_pid')
	dialogs = dialogs_for_process(setup_pid) if setup_pid else []
	app = Path(session['install_dir'])
	sentinel = app / 'Plugins' / 'Core' / SENTINEL_NAME
	return {
		'installer': {
			'running': bool(
				session.get('waiter_pid') and waiter_running and exit_result is None),
			'elapsed_seconds': max(0, time.time() - started) if started else None,
			'exit_code': None if exit_result is None else exit_result.get('exit_code'),
			'error': None if exit_result is None else exit_result.get('error'),
		},
		'message_box': dialogs[0].to_dict() if dialogs else None,
		'install': {
			'version': read_file_version(app / 'fman.exe'),
			'sentinel_present': sentinel.is_file(),
		},
		'fman_processes': processes_in_app(session),
	}


def close_window(index=0):
	processes = processes_in_app(_load_session())
	if index < 0 or index >= len(processes):
		raise ValueError('No fman process at index %s.' % index)
	windows = windows_for_pids({processes[index]['pid']})
	if not windows:
		raise RuntimeError('The selected fman process has no visible window.')
	close_native_window(windows[0].hwnd)
	return {'closed_pid': processes[index]['pid'], 'title': windows[0].title}


def answer(choice):
	if choice not in ('retry', 'cancel'):
		raise ValueError('Installer answer must be retry or cancel.')
	session = _load_session()
	_discover_setup_pid(session)
	dialogs = dialogs_for_process(session.get('setup_pid')) \
		if session.get('setup_pid') else []
	if not dialogs:
		raise RuntimeError(
			'No installer dialog is open for the recorded setup process.')
	control_id = 4 if choice == 'retry' else 2
	button = click_dialog_button(dialogs[0], control_id)
	return {
		'choice': choice, 'button': button.to_dict(),
		'dialog': dialogs[0].to_dict(),
	}


def cleanup():
	try:
		session = _load_session()
	except RuntimeError:
		return {'cleaned': False}
	_discover_setup_pid(session)
	install_dir = session.get('install_dir')
	if install_dir:
		kill_app_processes(install_dir)
	for key, time_key in (('setup_pid', 'setup_create_time'),
			('waiter_pid', 'waiter_create_time')):
		if session.get(key):
			terminate(session[key], session.get(time_key))
	snapshot = UserInstallSnapshot.from_dict(session['snapshot'])
	restored = restore_snapshot(snapshot, _registry())
	session_dir = Path(session['session_dir'])
	if session_dir.exists():
		try:
			shutil.rmtree(session_dir)
		except OSError:
			time.sleep(1)
			shutil.rmtree(session_dir)
	SESSION_FILE.unlink(missing_ok=True)
	return {'cleaned': True, **restored}


def run_installer(args):
	if args.installer_action == 'launch':
		return launch(args.setup, args.windows)
	if args.installer_action == 'update':
		return update()
	if args.installer_action == 'state':
		return state()
	if args.installer_action == 'close-window':
		return close_window(args.index)
	if args.installer_action == 'answer':
		return answer(args.choice)
	return cleanup()
