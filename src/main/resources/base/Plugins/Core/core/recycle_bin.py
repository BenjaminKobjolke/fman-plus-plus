"""Read and restore entries from the current user's Windows Recycle Bin."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from glob import glob
from os import remove, rename
from os.path import basename, dirname, isdir, join, lexists
import ntpath
import shutil
from fman.url import as_human_readable


@dataclass(frozen=True)
class RecycleBinEntry:
	original_path: str
	data_path: str
	info_path: str
	deleted_at: datetime
	size: int


def parse_entry(info_path):
	"""Parse one Windows `$I` metadata file and locate its matching `$R` data."""
	with open(info_path, 'rb') as file:
		data = file.read()
	if len(data) < 24:
		raise ValueError('Truncated Recycle Bin metadata')

	version = int.from_bytes(data[0:8], 'little', signed=True)
	size = int.from_bytes(data[8:16], 'little', signed=True)
	filetime = int.from_bytes(data[16:24], 'little', signed=False)
	if version == 1:
		if len(data) < 544:
			raise ValueError('Truncated version 1 Recycle Bin metadata')
		encoded_path = data[24:544]
	elif version == 2:
		if len(data) < 28:
			raise ValueError('Truncated version 2 Recycle Bin metadata')
		character_count = int.from_bytes(data[24:28], 'little', signed=True)
		if character_count < 1 or len(data) < 28 + character_count * 2:
			raise ValueError('Truncated version 2 Recycle Bin path')
		encoded_path = data[28:28 + character_count * 2]
	else:
		raise ValueError('Unsupported Recycle Bin metadata version: %s' % version)

	try:
		original_path = encoded_path.decode('utf-16-le').split('\0', 1)[0]
	except UnicodeDecodeError as error:
		raise ValueError('Invalid UTF-16 Recycle Bin path') from error
	if not original_path or size < 0:
		raise ValueError('Invalid Recycle Bin metadata')
	try:
		deleted_at = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(
			microseconds=filetime // 10
		)
	except OverflowError as error:
		raise ValueError('Invalid Recycle Bin deletion time') from error
	info_name = basename(info_path)
	if not info_name.startswith('$I'):
		raise ValueError('Not a Recycle Bin metadata file')
	data_path = join(dirname(info_path), '$R' + info_name[2:])
	return RecycleBinEntry(
		original_path, data_path, info_path, deleted_at, size
	)


def iter_entries(original_path):
	"""Yield readable current-user trash entries for the path's drive."""
	if original_path.startswith('file://'):
		original_path = as_human_readable(original_path)
	sid = get_current_user_sid()
	bin_directory = _recycle_bin_directory(original_path, sid)
	if not isdir(bin_directory):
		return
	for info_path in glob(join(bin_directory, '$I*')):
		try:
			entry = parse_entry(info_path)
		except (OSError, ValueError):
			continue
		if lexists(entry.data_path):
			yield entry


def find_entry(original_path):
	"""Return the newest current-user trash entry for an original path."""
	if original_path.startswith('file://'):
		original_path = as_human_readable(original_path)
	matches = (
		entry for entry in iter_entries(original_path)
		if entry.original_path.casefold() == original_path.casefold()
	)
	return max(matches, key=lambda entry: entry.deleted_at, default=None)


def restore_entry(entry):
	"""Move the trashed data back, then remove its metadata file."""
	if not lexists(entry.data_path):
		raise FileNotFoundError(entry.data_path)
	if lexists(entry.original_path):
		raise FileExistsError(entry.original_path)
	rename(entry.data_path, entry.original_path)
	remove(entry.info_path)


def remove_entry(entry):
	"""Permanently remove trashed data, then remove its metadata file."""
	if isdir(entry.data_path):
		shutil.rmtree(entry.data_path)
	else:
		remove(entry.data_path)
	remove(entry.info_path)


def get_current_user_sid():
	"""Return this process user's SID without relying on a localized account name."""
	import win32api
	import win32con
	import win32security

	token = win32security.OpenProcessToken(
		win32api.GetCurrentProcess(), win32con.TOKEN_QUERY
	)
	try:
		sid = win32security.GetTokenInformation(
			token, win32security.TokenUser
		)[0]
		return win32security.ConvertSidToStringSid(sid)
	finally:
		win32api.CloseHandle(token)


def _recycle_bin_directory(original_path, sid):
	drive, _ = ntpath.splitdrive(original_path)
	if not drive or not drive.endswith(':'):
		return ''
	return ntpath.join(drive + '\\', '$Recycle.Bin', sid)
