"""Settings and filesystem metadata shown by the overwrite dialog."""
from core.util import format_size
from core.settings import get_setting, SETTINGS_FILE
from fman import PLATFORM
from fman.impl.overwrite_dialog import FileDetails
from fman.url import basename, dirname, join, splitscheme

from dataclasses import replace
import os.path


SETTING_KEY = 'show_overwrite_details'


def is_enabled():
	return get_setting(SETTINGS_FILE, SETTING_KEY, True)


def get_details(fs, src, dest):
	if not is_enabled():
		return None
	existing = _file_details(fs, dest)
	incoming = _file_details(fs, src)
	try:
		existing_size = fs.query(dest, 'size_bytes')
		incoming_size = fs.query(src, 'size_bytes')
		if existing_size is not None and incoming_size is not None:
			existing = replace(existing, is_larger=existing_size > incoming_size)
			incoming = replace(incoming, is_larger=incoming_size > existing_size)
	except (OSError, TypeError):
		pass
	try:
		existing_modified = fs.query(dest, 'modified_datetime')
		incoming_modified = fs.query(src, 'modified_datetime')
		if existing_modified is not None and incoming_modified is not None:
			existing = replace(
				existing, is_newer=existing_modified > incoming_modified
			)
			incoming = replace(
				incoming, is_newer=incoming_modified > existing_modified
			)
	except (OSError, TypeError):
		pass
	return existing, incoming


def _file_details(fs, url):
	# Core imports commands before it defines the Modified column.
	from core import Modified
	try:
		size = fs.query(url, 'size_bytes')
		size_text = '' if size is None else format_size(size)
	except OSError:
		size_text = ''
	modified = Modified(fs).get_str(url)
	return FileDetails(size_text, modified, _version(url))


def _version(url):
	if PLATFORM != 'Windows':
		return ''
	try:
		scheme, path = splitscheme(url)
		if scheme != 'file://' or os.path.splitext(path)[1].lower() not in (
			'.exe', '.dll'
		):
			return ''
		import win32api
		version = win32api.GetFileVersionInfo(path, '\\')
		version_ms = version['FileVersionMS']
		version_ls = version['FileVersionLS']
		return '%d.%d.%d.%d' % (
			version_ms >> 16, version_ms & 0xffff,
			version_ls >> 16, version_ls & 0xffff,
		)
	except Exception:
		return ''


def free_name(url, is_taken):
	name = basename(url)
	stem, extension = os.path.splitext(name)
	directory = dirname(url)
	number = 2
	while True:
		candidate = join(directory, '%s (%d)%s' % (stem, number, extension))
		if not is_taken(candidate):
			return candidate
		number += 1
