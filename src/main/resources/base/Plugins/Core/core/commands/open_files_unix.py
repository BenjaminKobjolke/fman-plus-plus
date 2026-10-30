"""Open files using the native launchers on macOS and Linux."""
from subprocess import DEVNULL, Popen

import os


def _open_local_files_mac(paths):
	non_executables = []
	for path in paths:
		try:
			_run_executable(path)
		except (OSError, ValueError):
			non_executables.append(path)
	if non_executables:
		try:
			Popen(['open'] + non_executables, **_quiet)
		except OSError:
			pass


def _open_local_files_linux(paths):
	for path in paths:
		try:
			_run_executable(path)
		except (OSError, ValueError):
			try:
				Popen(['xdg-open', path], **_quiet)
			except Exception as e:
				raise e from None


def _run_executable(path):
	Popen([path], cwd=os.path.dirname(path), **_quiet)


_quiet = {'stdout': DEVNULL, 'stderr': DEVNULL}
