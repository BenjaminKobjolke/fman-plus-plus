"""Read and update Total Commander's per-directory ``descript.ion`` comments."""
from dataclasses import dataclass
from fman import PLATFORM
from os import path, remove, stat
from threading import RLock
from typing import Iterable, Optional

DESCRIPT_ION = 'descript.ion'
MULTILINE_TRAILER = '\x04Â'


def _normalize_name(name: str) -> str:
	return name.lower() if PLATFORM == 'Windows' else name


def _parse_line(line: str):
	if line.startswith('"'):
		end = line.find('"', 1)
		if end < 0 or end + 1 >= len(line) or line[end + 1] != ' ':
			return None
		name, comment = line[1:end], line[end + 2:]
	else:
		separator = line.find(' ')
		if separator <= 0:
			return None
		name, comment = line[:separator], line[separator + 1:]
	multiline = comment.endswith(MULTILINE_TRAILER)
	if multiline:
		comment = comment[:-len(MULTILINE_TRAILER)]
	comment = comment.replace('\\n', '\n')
	return name, comment


def _format_line(name: str, comment: str) -> str:
	formatted_name = '"%s"' % name if ' ' in name else name
	multiline = '\n' in comment
	formatted_comment = comment.replace('\n', '\\n')
	if multiline:
		formatted_comment += MULTILINE_TRAILER
	return '%s %s' % (formatted_name, formatted_comment)


class CommentFile:
	"""An editable comment file that retains lines it does not recognize."""
	def __init__(self, text: str, encoding: str = 'utf-8'):
		self.encoding = encoding
		self.raw_lines = text.splitlines()
		self.name_to_line_index: dict = {}
		self._names: dict = {}
		self._comments: dict = {}
		for index, line in enumerate(self.raw_lines):
			parsed = _parse_line(line)
			if parsed is None:
				continue
			name, comment = parsed
			key = _normalize_name(name)
			self.name_to_line_index[key] = index
			self._names[key] = name
			self._comments[key] = comment

	def get(self, name: str) -> Optional[str]:
		return self._comments.get(_normalize_name(name))

	def set(self, name: str, comment: str) -> None:
		key = _normalize_name(name)
		if not comment:
			self.remove(name)
			return
		line = _format_line(self._names.get(key, name), comment)
		if key in self.name_to_line_index:
			self.raw_lines[self.name_to_line_index[key]] = line
		else:
			self.name_to_line_index[key] = len(self.raw_lines)
			self._names[key] = name
			self.raw_lines.append(line)
		self._comments[key] = comment

	def remove(self, name: str) -> None:
		key = _normalize_name(name)
		index = self.name_to_line_index.pop(key, None)
		if index is None:
			return
		self.raw_lines.pop(index)
		self._names.pop(key, None)
		self._comments.pop(key, None)
		for other_key, other_index in tuple(self.name_to_line_index.items()):
			if other_index > index:
				self.name_to_line_index[other_key] = other_index - 1

	def entries(self) -> list:
		return [
			(self._names[key], self._comments[key])
			for key in self.name_to_line_index
		]

	def to_text(self) -> str:
		return '\r\n'.join(self.raw_lines)


@dataclass
class _CachedCommentFile:
	stat_signature: tuple
	comments: CommentFile


_cache = {}
_lock = RLock()


def _directory_for_url(url: str) -> Optional[str]:
	file_path = _path_for_url(url)
	return None if file_path is None else path.dirname(file_path)


def _path_for_url(url: str) -> Optional[str]:
	if not isinstance(url, str) or not url.startswith('file://'):
		return None
	return url[len('file://'):]


def _read_bytes(data: bytes):
	if data.startswith(b'\xef\xbb\xbf'):
		return data.decode('utf-8-sig'), 'utf-8-sig'
	try:
		return data.decode('utf-8'), 'utf-8'
	except UnicodeDecodeError:
		encoding = 'mbcs' if PLATFORM == 'Windows' else 'latin-1'
		return data.decode(encoding), encoding


def _stat_signature(file_path: str) -> Optional[tuple]:
	try:
		file_stat = stat(file_path)
		return file_stat.st_mtime_ns, file_stat.st_size
	except FileNotFoundError:
		return None


def _load(directory: str) -> CommentFile:
	file_path = path.join(directory, DESCRIPT_ION)
	with _lock:
		signature = _stat_signature(file_path)
		cached = _cache.get(directory)
		if cached is not None and cached.stat_signature == signature:
			return cached.comments
		if signature is None:
			comments = CommentFile('', 'utf-8-sig')
		else:
			with open(file_path, 'rb') as file:
				text, encoding = _read_bytes(file.read())
			comments = CommentFile(text, encoding)
		_cache[directory] = _CachedCommentFile(signature, comments)
		return comments


def _set_hidden(file_path: str) -> None:
	if PLATFORM != 'Windows':
		return
	import ctypes
	import ctypes.wintypes
	import os
	from stat import FILE_ATTRIBUTE_HIDDEN

	kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
	kernel32.SetFileAttributesW.argtypes = (
		ctypes.wintypes.LPCWSTR, ctypes.wintypes.DWORD
	)
	kernel32.SetFileAttributesW.restype = ctypes.wintypes.BOOL
	attributes = os.lstat(file_path).st_file_attributes
	if not kernel32.SetFileAttributesW(
		file_path, attributes | FILE_ATTRIBUTE_HIDDEN
	):
		raise ctypes.WinError(ctypes.get_last_error())


def _write(directory: str, comments: CommentFile) -> None:
	file_path = path.join(directory, DESCRIPT_ION)
	with _lock:
		existed = path.exists(file_path)
		if not comments.entries():
			if existed:
				remove(file_path)
			_cache.pop(directory, None)
			return
		text = comments.to_text()
		try:
			data = text.encode(comments.encoding)
		except UnicodeEncodeError:
			comments.encoding = 'utf-8-sig'
			data = text.encode(comments.encoding)
		with open(file_path, 'r+b' if existed else 'wb') as file:
			file.seek(0)
			file.write(data)
			file.truncate()
		if not existed:
			_set_hidden(file_path)
		_cache.pop(directory, None)


def get_comment(url: str) -> Optional[str]:
	directory = _directory_for_url(url)
	if directory is None:
		return None
	with _lock:
		return _load(directory).get(path.basename(url[len('file://'):]))


def has_comments(url: str) -> bool:
	directory = _path_for_url(url)
	if directory is None:
		return False
	with _lock:
		return bool(_load(directory).entries())


def set_comment(urls: Iterable[str], comment: str) -> None:
	by_directory = {}
	for url in urls:
		directory = _directory_for_url(url)
		if directory is not None:
			by_directory.setdefault(directory, []).append(
				(path.basename(url[len('file://'):]), comment)
			)
	for directory, updates in by_directory.items():
		with _lock:
			comments = _load(directory)
			for name, text in updates:
				comments.set(name, text)
			_write(directory, comments)


def copy_comments(transfers: Iterable[tuple]) -> None:
	for source, destination in transfers:
		comment = get_comment(source)
		if comment is not None and _directory_for_url(destination) is not None:
			set_comment([destination], comment)


def move_comments(transfers: Iterable[tuple]) -> None:
	comments = []
	for source, destination in transfers:
		if _directory_for_url(source) is None or \
				_directory_for_url(destination) is None:
			continue
		comments.append((source, destination, get_comment(source)))
	for _source, destination, comment in comments:
		if comment is not None:
			set_comment([destination], comment)
	for source, destination, comment in comments:
		same_entry = (
			_directory_for_url(source) == _directory_for_url(destination) and
			_normalize_name(path.basename(source[len('file://'):])) ==
			_normalize_name(path.basename(destination[len('file://'):]))
		)
		if comment is not None and not same_entry:
			remove_comments([source])


def remove_comments(urls: Iterable[str]) -> list:
	removed = []
	by_directory = {}
	for url in urls:
		directory = _directory_for_url(url)
		if directory is not None:
			by_directory.setdefault(directory, []).append(url)
	for directory, directory_urls in by_directory.items():
		with _lock:
			comments = _load(directory)
			for url in directory_urls:
				name = path.basename(url[len('file://'):])
				comment = comments.get(name)
				if comment is not None:
					removed.append((url, comment))
					comments.remove(name)
			_write(directory, comments)
	return removed


def restore_comments(comments: Iterable[tuple]) -> None:
	for url, comment in comments:
		set_comment([url], comment)
