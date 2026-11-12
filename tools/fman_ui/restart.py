"""Stop and restart an isolated fman process without deleting its profile."""

from pathlib import Path
import json
import time
from urllib.error import URLError

import psutil

from session_reaper import (
	RESTART_MARKER, kill_process,
)


QUIT_TIMEOUT_SECONDS = 15


def clear_restart_marker(session_root):
	(Path(session_root) / RESTART_MARKER).unlink(missing_ok=True)


def _process_is_running(pid, start_time):
	try:
		process = psutil.Process(pid)
		return abs(process.create_time() - start_time) <= 1
	except psutil.NoSuchProcess:
		return False


def _wait_for_exit(session):
	pid = session.get('fman_pid', session['pid'])
	start_time = session.get('fman_start_time', session['start_time'])
	deadline = time.monotonic() + QUIT_TIMEOUT_SECONDS
	while time.monotonic() < deadline:
		if not _process_is_running(pid, start_time):
			return
		time.sleep(.25)
	if _process_is_running(pid, start_time):
		kill_process(pid, start_time)


def stop_for_restart(session, api):
	session_root = Path(session['profile']).parent
	(session_root / RESTART_MARKER).touch()
	try:
		api(session, 'POST', '/v1/command', {
			'name': 'quit', 'args': {}, 'pane': 0,
		})
	except (OSError, RuntimeError, URLError):
		pass
	_wait_for_exit(session)
	return session_root


def restart_session(session, api, start_fman, current_path):
	session_root = stop_for_restart(session, api)
	try:
		state = start_fman(session, session_root)
	finally:
		clear_restart_marker(session_root)
	Path(current_path).write_text(json.dumps(session, indent=2),
		encoding='utf-8')
	return state
