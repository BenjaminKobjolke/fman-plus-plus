"""Read virtual files that Windows sources provide without filesystem paths."""

import os
import re
import shutil
import struct
import tempfile
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from fman.url import as_url

FILE_GROUP_DESCRIPTOR_FORMAT = 'FileGroupDescriptorW'
FILE_CONTENTS_FORMAT = 'FileContents'
TEMP_FOLDER_NAME = 'fman virtual files'
_DESCRIPTOR_SIZE = 592
_FD_ATTRIBUTES = 0x4
_FD_FILESIZE = 0x40
_FILE_ATTRIBUTE_DIRECTORY = 0x10
_MAX_PATH_COMPONENT = 255
_RESERVED_NAMES = frozenset(
	['CON', 'PRN', 'AUX', 'NUL'] +
	['COM%d' % number for number in range(1, 10)] +
	['LPT%d' % number for number in range(1, 10)]
)


def _clipboard_format(name):
	import win32clipboard
	return win32clipboard.RegisterClipboardFormat(name)


def _parse_file_group_descriptor(blob):
	count = struct.unpack_from('<I', blob)[0]
	if len(blob) < 4 + count * _DESCRIPTOR_SIZE:
		raise ValueError('Invalid FILEGROUPDESCRIPTORW size')
	files = []
	for index in range(count):
		offset = 4 + index * _DESCRIPTOR_SIZE
		attributes = struct.unpack_from('<I', blob, offset + 36)[0]
		has_attributes = bool(attributes & _FD_ATTRIBUTES)
		has_size = bool(attributes & _FD_FILESIZE)
		size_high, size_low = struct.unpack_from('<II', blob, offset + 64)
		name_data = blob[offset + 72:offset + 72 + 520]
		name = name_data.decode('utf-16le').split('\0', 1)[0]
		files.append({
			'name': name,
			'is_directory': has_attributes and bool(
				attributes & _FILE_ATTRIBUTE_DIRECTORY),
			'size': (size_high << 32) | size_low if has_size else None
		})
	return files


def _sanitize_name(name, used, is_directory=False):
	parts = []
	for part in name.replace('\\', '/').split('/'):
		part = re.sub(r'[\x00-\x1f<>:"/|?*]', '_', part).strip().rstrip('. ')
		if part in ('', '.', '..'):
			part = 'unnamed'
		if part.split('.')[0].upper() in _RESERVED_NAMES:
			part = '_' + part
		parts.append(part[:_MAX_PATH_COMPONENT])
	if not parts:
		parts = ['unnamed']
	path = '/'.join(parts)
	def conflicts(candidate):
		key = candidate.casefold()
		candidate_parts = candidate.split('/')
		prefixes = ['/'.join(candidate_parts[:index]).casefold()
			for index in range(1, len(candidate_parts))]
		return any(used.get(prefix) is False for prefix in prefixes) or \
			(key in used and not (is_directory and used[key])) or \
			(not is_directory and any(
				entry.startswith(key + '/') for entry in used))
	if conflicts(path):
		conflicting_parent = next((index - 1 for index in range(1, len(parts))
			if used.get('/'.join(parts[:index]).casefold()) is False), None)
		if conflicting_parent is None:
			conflicting_parent = len(parts) - 1
		conflicting_base, conflicting_extension = os.path.splitext(
			parts[conflicting_parent])
		number = 2
		candidate_parts = parts[:conflicting_parent] + [
			'%s (%d)%s' % (conflicting_base, number, conflicting_extension)
		] + parts[conflicting_parent + 1:]
		candidate = '/'.join(candidate_parts)
		while conflicts(candidate):
			number += 1
			candidate_parts[conflicting_parent] = '%s (%d)%s' % (
				conflicting_base, number, conflicting_extension)
			candidate = '/'.join(candidate_parts)
		path = candidate
	for index in range(1, len(parts)):
		used.setdefault('/'.join(parts[:index]).casefold(), True)
	used[path.casefold()] = is_directory
	return path


def _medium_data(medium):
	return getattr(medium, 'data', medium)


def _write_stream(stream, path):
	with open(path, 'wb') as file:
		while True:
			chunk = stream.Read(1024 * 1024)
			if isinstance(chunk, tuple):
				chunk = chunk[0]
			if not chunk:
				break
			file.write(chunk)


def _write_storage(source, path):
	import pythoncom
	from win32com import storagecon

	destination = pythoncom.StgCreateDocfile(
		path,
		storagecon.STGM_CREATE | storagecon.STGM_READWRITE |
		storagecon.STGM_SHARE_EXCLUSIVE,
		0
	)
	try:
		source.CopyTo([], None, destination)
		destination.Commit(0)
	finally:
		destination = None


def _prune_old_batches(root):
	cutoff = datetime.now().timestamp() - timedelta(days=1).total_seconds()
	try:
		entries = os.scandir(root)
	except FileNotFoundError:
		return
	with entries:
		for entry in entries:
			if entry.is_dir(follow_symlinks=False) and entry.stat(
				follow_symlinks=False).st_mtime < cutoff:
				shutil.rmtree(entry.path, ignore_errors=True)


def has_virtual_files(data_object: Any) -> bool:
	if data_object is None:
		return False
	import pythoncom

	try:
		data_object.QueryGetData((
			_clipboard_format(FILE_GROUP_DESCRIPTOR_FORMAT), None,
			pythoncom.DVASPECT_CONTENT, -1, pythoncom.TYMED_HGLOBAL
		))
		return True
	except Exception:
		return False


def save_virtual_files(data_object: Any) -> list[str]:
	import pythoncom

	cf_descriptor = _clipboard_format(FILE_GROUP_DESCRIPTOR_FORMAT)
	medium = data_object.GetData((
		cf_descriptor, None, pythoncom.DVASPECT_CONTENT, -1,
		pythoncom.TYMED_HGLOBAL
	))
	blob = _medium_data(medium)
	descriptors = _parse_file_group_descriptor(bytes(blob))
	root = os.path.join(tempfile.gettempdir(), TEMP_FOLDER_NAME)
	_prune_old_batches(root)
	batch = os.path.join(root, str(uuid4()))
	os.makedirs(batch)
	used = {}
	top_level = []
	try:
		for index, descriptor in enumerate(descriptors):
			name = _sanitize_name(descriptor['name'], used,
				descriptor['is_directory'])
			path = os.path.join(batch, *name.split('/'))
			if descriptor['is_directory']:
				os.makedirs(path, exist_ok=True)
			else:
				os.makedirs(os.path.dirname(path), exist_ok=True)
				contents = data_object.GetData((
					_clipboard_format(FILE_CONTENTS_FORMAT), None,
					pythoncom.DVASPECT_CONTENT, index,
					pythoncom.TYMED_HGLOBAL | pythoncom.TYMED_ISTREAM |
					pythoncom.TYMED_ISTORAGE
				))
				tymed = contents.tymed
				content = _medium_data(contents)
				if tymed == pythoncom.TYMED_HGLOBAL:
					data = bytes(content)
					if descriptor['size'] is not None:
						data = data[:descriptor['size']]
					with open(path, 'wb') as file:
						file.write(data)
				elif tymed == pythoncom.TYMED_ISTREAM:
					_write_stream(content, path)
				elif tymed == pythoncom.TYMED_ISTORAGE:
					_write_storage(content, path)
				else:
					raise ValueError('Unsupported virtual file medium: %r' % tymed)
			if name.split('/')[0] not in top_level:
				top_level.append(name.split('/')[0])
		return [as_url(os.path.join(batch, name)) for name in top_level]
	except BaseException:
		shutil.rmtree(batch, ignore_errors=True)
		raise


def get_clipboard_data_object() -> Any | None:
	import pythoncom
	try:
		return pythoncom.OleGetClipboard()
	except pythoncom.com_error:
		return None
