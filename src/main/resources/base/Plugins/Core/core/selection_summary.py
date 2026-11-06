"""Measure and format the files and folders selected in a pane."""
from dataclasses import dataclass
from enum import Enum

from core.settings import get_setting, SETTINGS_FILE
from core.util import format_size
import fman.fs as default_fs


SUMMARY_LOCATION_KEY = 'selection_summary_location'
FOLDER_SIZES_KEY = 'selection_summary_folder_sizes'
DEFAULT_SUMMARY_LOCATION = 'pane'
DEFAULT_FOLDER_SIZES = False


class SelectionSummaryLocation(Enum):
	PANE = 'pane'
	WINDOW = 'window'
	BOTH = 'both'


@dataclass(frozen=True)
class SelectionStats:
	file_count: int
	folder_count: int
	size_bytes: int | None
	calculating: bool = False


def get_summary_location():
	value = get_setting(
		SETTINGS_FILE, SUMMARY_LOCATION_KEY, DEFAULT_SUMMARY_LOCATION,
	)
	try:
		return SelectionSummaryLocation(value)
	except (TypeError, ValueError):
		return SelectionSummaryLocation.PANE


def get_folder_sizes_enabled():
	value = get_setting(
		SETTINGS_FILE, FOLDER_SIZES_KEY, DEFAULT_FOLDER_SIZES,
	)
	return value if type(value) is bool else DEFAULT_FOLDER_SIZES


def measure(selected_urls, recursive=False, fs=None, is_cancelled=None):
	"""Return selected counts and file size, optionally walking selected folders.

	`fs` and `is_cancelled` keep filesystem work testable and allow a caller to
	stop a stale background measurement when the selection changes.
	"""
	filesystem = default_fs if fs is None else fs
	should_cancel = is_cancelled or (lambda: False)
	file_count = 0
	folder_count = 0
	total_size = 0
	has_size = False
	calculating = False
	visited = set()

	def add_file(url, selected=False):
		nonlocal file_count, total_size, has_size
		if selected:
			file_count += 1
		try:
			size = filesystem.query(url, 'size_bytes')
		except OSError:
			return
		if size is not None:
			total_size += size
			has_size = True

	def walk(url):
		nonlocal calculating
		try:
			resolved = filesystem.resolve(url)
			if resolved in visited:
				return
			visited.add(resolved)
			children = iter(filesystem.iterdir(url))
		except OSError:
			return
		while True:
			if should_cancel():
				calculating = True
				return
			try:
				child = next(children)
			except StopIteration:
				return
			except OSError:
				return
			try:
				is_directory = filesystem.is_dir(child)
			except OSError:
				continue
			if is_directory:
				walk(child)
				if calculating:
					return
			else:
				add_file(child)

	for url in selected_urls:
		if should_cancel():
			calculating = True
			break
		try:
			is_directory = filesystem.is_dir(url)
		except OSError:
			continue
		if is_directory:
			folder_count += 1
			if recursive:
				walk(url)
				if calculating:
					break
		else:
			add_file(url, selected=True)

	size_bytes = total_size if has_size or recursive else None
	return SelectionStats(file_count, folder_count, size_bytes, calculating)


def format_summary(stats):
	parts = []
	if stats.file_count:
		unit = 'file' if stats.file_count == 1 else 'files'
		parts.append('%d %s' % (stats.file_count, unit))
	if stats.folder_count:
		unit = 'folder' if stats.folder_count == 1 else 'folders'
		parts.append('%d %s' % (stats.folder_count, unit))
	if parts:
		parts[-1] += ' selected'
	if stats.size_bytes is not None:
		parts.append(format_size(stats.size_bytes))
	if stats.calculating:
		parts.append('calculating...')
	return ', '.join(parts)
