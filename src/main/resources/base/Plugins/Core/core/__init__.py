# Re-exported so the plugin loader discovers the Viewer subclasses: it only
# scans names reachable from this module (plugin.py:_iterate_classes).
from importlib import import_module as _import_module
from datetime import datetime
from fman.fs import Column
from fman.url import basename
from PyQt5.QtCore import QLocale, QDateTime
from .util import format_size

import fman.fs
import re

for _module_name in ('.commands', '.fs', '.viewers'):
	_module = _import_module(_module_name, __name__)
	_module_names = getattr(
		_module, '__all__',
		(name for name in vars(_module) if not name.startswith('_'))
	)
	for _name in _module_names:
		globals()[_name] = getattr(_module, _name)

# Define here so get_default_columns(...) can reference it as core.Name:
class Name(Column):
	def __init__(self, fs=fman.fs):
		super().__init__()
		self._fs = fs
	def get_str(self, url):
		return self._fs.query(url, 'name')
	def get_sort_value(self, url, is_ascending):
		try:
			is_dir = self._fs.is_dir(url)
		except FileNotFoundError:
			raise
		except OSError:
			is_dir = False
		major = is_dir ^ is_ascending
		str_ = self.get_str(url).lower()
		minor = ''
		while str_:
			match = re.search(r'\d+', str_)
			if match:
				minor += str_[:match.start()]
				minor += '%06d' % int(match.group(0))
				str_ = str_[match.end():]
			else:
				minor += str_
				break
		return major, minor

# Define here so get_default_columns(...) can reference it as core.Size:
class Size(Column):
	def __init__(self, fs=fman.fs):
		super().__init__()
		self._fs = fs
	def get_str(self, url):
		try:
			is_dir = self._fs.is_dir(url)
		except FileNotFoundError:
			raise
		except OSError:
			return ''
		if is_dir:
			return ''
		try:
			size_bytes = self._get_size(url)
		except OSError:
			return ''
		if size_bytes is None:
			return ''
		return format_size(size_bytes)
	def get_sort_value(self, url, is_ascending):
		try:
			is_dir = self._fs.is_dir(url)
		except FileNotFoundError:
			raise
		except OSError:
			is_dir = False
		if is_dir:
			ord_ = ord if is_ascending else lambda c: -ord(c)
			minor = tuple(ord_(c) for c in basename(url).lower())
		else:
			try:
				minor = self._get_size(url)
			except OSError:
				minor = 0
		return is_dir ^ is_ascending, minor
	def _get_size(self, url):
		return self._fs.query(url, 'size_bytes')

# Define here so get_default_columns(...) can reference it as core.Modified:
class Modified(Column):
	def __init__(self, fs=fman.fs):
		super().__init__()
		self._fs = fs
	def get_str(self, url):
		try:
			mtime = self._get_mtime(url)
		except OSError:
			return ''
		if mtime is None:
			return ''
		try:
			timestamp = mtime.timestamp()
		except OSError:
			# This can occur on Windows. To reproduce:
			#     datetime.min.timestamp()
			# This raises `OSError: [Errno 22] Invalid argument`.
			return ''
		mtime_qt = QDateTime.fromMSecsSinceEpoch(int(timestamp * 1000))
		time_format = QLocale().dateTimeFormat(QLocale.ShortFormat)
		# Always show two-digit years, not four digits:
		time_format = time_format.replace('yyyy', 'yy')
		return mtime_qt.toString(time_format)
	def get_sort_value(self, url, is_ascending):
		try:
			is_dir = self._fs.is_dir(url)
		except FileNotFoundError:
			raise
		except OSError:
			is_dir = False
		try:
			mtime = self._get_mtime(url)
		except OSError:
			mtime = None
		return is_dir ^ is_ascending, mtime or datetime.min
	def _get_mtime(self, url):
		return self._fs.query(url, 'modified_datetime')
