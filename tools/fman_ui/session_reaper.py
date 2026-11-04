"""Close abandoned fman UI test sessions after their driver stops using them."""

import json
from pathlib import Path
import shutil
import sys
import time

import psutil

from recycle_cleanup import cleanup_session


IDLE_LIMIT_SECONDS = 30 * 60
WATCH_INTERVAL_SECONDS = 30
SESSION_FILE = 'session.json'


def process_start_time(pid):
	return psutil.Process(pid).create_time()


def fman_process_identity(pid):
	"""Return the Python child identity when a launcher owns the process."""
	try:
		children = psutil.Process(pid).children(recursive=True)
	except psutil.NoSuchProcess:
		return None
	python_children = []
	for child in children:
		try:
			if Path(child.exe()).name.lower() in ('python.exe', 'pythonw.exe'):
				python_children.append((child.pid, child.create_time()))
		except psutil.Error:
			continue
	if not python_children:
		return None
	return python_children[-1]


def kill_process(pid, start_time):
	try:
		process = psutil.Process(pid)
		if abs(process.create_time() - start_time) > 1:
			return
		processes = process.children(recursive=True) + [process]
	except psutil.NoSuchProcess:
		return

	for item in processes:
		try:
			item.kill()
		except psutil.NoSuchProcess:
			pass
	psutil.wait_procs(processes, timeout=5)


def close_session(session_root):
	session_root = Path(session_root)
	session_file = session_root / SESSION_FILE
	if session_file.exists():
		session = json.loads(session_file.read_text(encoding='utf-8'))
		kill_process(session.get('fman_pid', session['pid']),
			session.get('fman_start_time', session['start_time']))
	try:
		removed = cleanup_session(session_root)
	except OSError:
		removed = 0
	shutil.rmtree(session_root, ignore_errors=True)
	return removed


def is_stale(session_root, now):
	session_root = Path(session_root)
	session_file = session_root / SESSION_FILE
	if not session_file.exists():
		return now - session_root.stat().st_mtime > IDLE_LIMIT_SECONDS
	if now - session_file.stat().st_mtime > IDLE_LIMIT_SECONDS:
		return True
	session = json.loads(session_file.read_text(encoding='utf-8'))
	pid = session.get('fman_pid', session['pid'])
	start_time = session.get('fman_start_time', session['start_time'])
	try:
		return abs(psutil.Process(pid).create_time() - start_time) > 1
	except psutil.NoSuchProcess:
		return True


def reap_stale(root, now):
	root = Path(root)
	if not root.exists():
		return
	for session_root in root.iterdir():
		if session_root.is_dir() and is_stale(session_root, now):
			close_session(session_root)


def watch(session_root):
	session_root = Path(session_root)
	while session_root.exists():
		time.sleep(WATCH_INTERVAL_SECONDS)
		if session_root.exists() and is_stale(session_root, time.time()):
			close_session(session_root)
			return


if __name__ == '__main__':
	watch(Path(sys.argv[1]))
