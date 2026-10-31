from fman.url import dirname
from os import listdir, strerror
from os.path import join
from pathlib import PurePosixPath

import errno
import fman.fs
import os
from math import log
from os.path import pardir
from fman import PLATFORM

def is_relative_name(name):
	"""Return whether name identifies one file, rather than a relative path."""
	return not (
		os.sep in name or name in (pardir, '.')
		or (PLATFORM == 'Windows' and '/' in name)
	)

def format_size(size_bytes):
	units = ('%d B', '%d KB', '%.1f MB', '%.1f GB', '%.1f TB')
	if size_bytes <= 0:
		unit_index = 0
	else:
		unit_index = min(int(log(size_bytes, 1000)), len(units) - 1)
	unit = units[unit_index]
	base = 1024 ** unit_index
	return unit % (size_bytes / base)

def strformat_dict_values(dict_, replacements):
	result = {}
	def replace(value):
		if isinstance(value, str):
			return value.format(**replacements)
		return value
	for key, value in dict_.items():
		if isinstance(value, list):
			value = list(map(replace, value))
		else:
			value = replace(value)
		result[key] = value
	return result

def listdir_absolute(dir_path):
	return [join(dir_path, file_name) for file_name in listdir(dir_path)]

def filenotfounderror(path):
	# The correct way of instantiating FileNotFoundError in a way that respects
	# the parent class (OSError)'s arguments:
	return FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT), path)

def parent(path):
	if path == '/':
		return ''
	result = str(PurePosixPath(path).parent) if path else ''
	return '' if result == '.' else result

def is_parent(dir_url, file_url, fs=fman.fs):
	for parent_url in _iter_parents(file_url):
		try:
			if fs.samefile(parent_url, dir_url):
				return True
		except FileNotFoundError:
			continue
	return False

def _iter_parents(url):
	while True:
		yield url
		new_url = dirname(url)
		if new_url == url:
			break
		url = new_url
