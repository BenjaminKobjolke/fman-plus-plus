"""Find and stop only processes owned by a throwaway installer session."""

import os

import psutil

from native_dialogs import window_titles


def process_is_running(pid):
	try:
		return psutil.Process(pid).is_running()
	except (psutil.NoSuchProcess, psutil.AccessDenied):
		return False


def _inside(path, parent):
	try:
		path = os.path.normcase(os.path.abspath(path))
		parent = os.path.normcase(os.path.abspath(parent))
		return os.path.commonpath((path, parent)) == parent
	except (ValueError, OSError):
		return False


def fman_processes(session):
	processes = []
	for process in psutil.process_iter():
		try:
			exe = process.exe()
			if not exe or not _inside(exe, session['install_dir']):
				continue
			created = process.create_time()
			processes.append({
				'pid': process.pid, 'create_time': created,
				'started_after_update': bool(session.get('update_started_at')
					and created >= session['update_started_at']),
				'window_titles': window_titles(process.pid),
			})
		except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
			continue
	return sorted(processes, key=lambda item: (item['create_time'], item['pid']))


def _terminate(pid, expected_create_time=None):
	try:
		process = psutil.Process(pid)
		if expected_create_time is not None and abs(
				process.create_time() - expected_create_time) > 1:
			return False
		process.terminate()
		try:
			process.wait(timeout=3)
		except psutil.TimeoutExpired:
			process.kill()
		return True
	except (psutil.NoSuchProcess, psutil.AccessDenied):
		return False


def kill_app_processes(install_dir):
	for process in psutil.process_iter():
		try:
			if _inside(process.exe(), install_dir):
				_terminate(process.pid, process.create_time())
		except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
			continue


def terminate(pid, expected_create_time=None):
	return _terminate(pid, expected_create_time)
