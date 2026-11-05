# Re-exported so the plugin loader discovers the Viewer subclasses: it only
# scans names reachable from this module (plugin.py:_iterate_classes).
from importlib import import_module as _import_module
from datetime import datetime
import fman.fs
import re
from fman.fs import Column
from fman.url import basename
from PyQt5.QtCore import QLocale, QDate, QDateTime, QTime
from .util import format_size
from .file_extension import name_for_name_column
from .mixed_sort import DirsFirstColumn


def _format_mtime(mtime_qt):
	time_format = QLocale().dateTimeFormat(QLocale.ShortFormat)
	# Always show two-digit years, not four digits:
	time_format = time_format.replace('yyyy', 'yy')
	return mtime_qt.toString(time_format)

for _module_name in ('.commands', '.fs', '.viewers'):
	_module = _import_module(_module_name, __name__)
	_module_names = getattr(
		_module, '__all__',
		(name for name in vars(_module) if not name.startswith('_'))
	)
	for _name in _module_names:
		globals()[_name] = getattr(_module, _name)

# Define here so get_default_columns(...) can reference it as core.Name:
class Name(DirsFirstColumn, Column):
	def __init__(self, fs=fman.fs):
		super().__init__()
		self._fs = fs
	def get_str(self, url):
		return name_for_name_column(self._fs, url)
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
class Size(DirsFirstColumn, Column):
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
	def get_widest_str(self) -> str:
		# The largest supported file size keeps the Size column from truncating.
		return format_size(999_999_999)
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
	def get_mixed_sort_value(self, url, is_ascending):
		try:
			is_dir = self._fs.is_dir(url)
		except FileNotFoundError:
			raise
		except OSError:
			is_dir = False
		if is_dir:
			size = 0
		else:
			try:
				size = self._get_size(url)
			except OSError:
				size = 0
		if size is None:
			size = 0
		name = Name(self._fs).get_sort_value(url, is_ascending)[1]
		return size, name
	def _get_size(self, url):
		return self._fs.query(url, 'size_bytes')

# Define here so get_default_columns(...) can reference it as core.Modified:
class Modified(DirsFirstColumn, Column):
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
		return _format_mtime(mtime_qt)
	def get_widest_str(self) -> str:
		return _format_mtime(
			QDateTime(QDate(2000, 12, 28), QTime(22, 58, 58))
		)
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

# Export after Name because Extension uses it; the plugin loader discovers these
# columns here.
_file_columns = _import_module('.file_columns', __name__)
Attributes = _file_columns.Attributes
Extension = _file_columns.Extension
Version = _file_columns.Version
