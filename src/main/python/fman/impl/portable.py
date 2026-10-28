"""Select and validate the profile directory used by a portable Windows build."""

import os
import sys
import tempfile


MARKER_NAME = 'portable.txt'
DATA_FOLDER_NAME = 'Data'


def portable_app_dir():
	"""Return the frozen Windows app directory when its portable marker exists."""
	if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
		return None

	app_dir = os.path.dirname(sys.executable)
	if os.path.isfile(os.path.join(app_dir, MARKER_NAME)):
		return app_dir
	return None


def portable_data_directory():
	"""Return the Data directory for a marked portable app, if enabled."""
	app_dir = portable_app_dir()
	if app_dir is None:
		return None
	return os.path.join(app_dir, DATA_FOLDER_NAME)


def check_writable(path):
	"""Create a directory and probe that it can create and remove a file."""
	try:
		os.makedirs(path, exist_ok=True)
		with tempfile.NamedTemporaryFile(dir=path) as probe:
			probe.write(b'fman')
			probe.flush()
		return None
	except OSError as error:
		return error
