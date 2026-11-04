"""Windows read-only attribute helpers for local file replacement."""
from contextlib import contextmanager
import os
import stat


def is_read_only(os_path):
	attribute = getattr(stat, 'FILE_ATTRIBUTE_READONLY', None)
	if attribute is None:
		return False
	try:
		attributes = getattr(os.lstat(os_path), 'st_file_attributes', 0)
	except OSError:
		return False
	return bool(attributes & attribute)


@contextmanager
def writable_destination(os_path):
	if not is_read_only(os_path):
		yield
		return
	original_mode = os.stat(os_path).st_mode
	os.chmod(os_path, original_mode | stat.S_IWRITE)
	try:
		yield
	except BaseException:
		try:
			os.chmod(os_path, original_mode)
		except OSError:
			# The replacement may already have removed the original file.
			pass
		raise
