"""Helpers for detached fman processes and connection diagnostics."""

import os
from pathlib import Path
import subprocess

import psutil


def detached_popen(args, **kwargs):
	if os.name != 'nt':
		return subprocess.Popen(args, start_new_session=True, **kwargs)

	flags = (
		getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
		| getattr(subprocess, 'DETACHED_PROCESS', 0)
	)
	breakaway = getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0)
	try:
		# Sandboxed command jobs can kill child processes when the command ends.
		return subprocess.Popen(args, creationflags=flags | breakaway, **kwargs)
	except OSError as error:
		if getattr(error, 'winerror', None) != 5:
			raise
		return subprocess.Popen(args, creationflags=flags, **kwargs)


def log_tail(log_path, lines=40):
	try:
		return Path(log_path).read_text(
			encoding='utf-8', errors='replace').splitlines()[-lines:]
	except OSError:
		return []


def describe_refused(session):
	pid = session.get('fman_pid', session['pid'])
	start_time = session.get('fman_start_time', session['start_time'])
	identity_matches = False
	try:
		identity_matches = abs(psutil.Process(pid).create_time() - start_time) <= 1
	except psutil.NoSuchProcess:
		pass
	if identity_matches:
		return (
			'fman (pid %d) of session %s is running but refuses connections '
			'on port %d' % (pid, session['session_id'], session['port'])
		)

	log_path = Path(session['profile']).parent / 'fman.log'
	return (
		'fman (pid %d) of session %s has exited; log tail: %s'
		% (pid, session['session_id'], '\n'.join(log_tail(log_path)))
	)
