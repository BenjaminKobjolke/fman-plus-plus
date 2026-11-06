from fman.impl.util import Event
from fman.url import splitscheme


class ColumnSets:
	"""Own plugin overrides for filesystem and directory column sets."""

	def __init__(self, settings, get_registered_column_names):
		self._settings = settings
		self._get_registered_column_names = get_registered_column_names
		self._default_columns = {}
		self.changed = Event()

	def get_columns(self, url, default_columns):
		scheme = splitscheme(url)[0]
		folder_columns = self._get_available_columns(
			self._settings.get(url, None)
		)
		if folder_columns:
			return folder_columns
		scheme_columns = self._get_available_columns(
			self._default_columns.get(scheme)
		)
		if scheme_columns:
			return scheme_columns
		return tuple(default_columns)

	def set_default_columns(self, scheme, column_names):
		column_names = self._validate_column_names(column_names)
		self._default_columns[scheme] = column_names
		self.changed.trigger(scheme)

	def reset_default_columns(self, scheme):
		if scheme in self._default_columns:
			del self._default_columns[scheme]
			self.changed.trigger(scheme)

	def set_columns(self, url, column_names):
		column_names = self._validate_column_names(column_names)
		self._settings[url] = list(column_names)
		self._flush_settings()
		self.changed.trigger(url)

	def reset_columns(self, url):
		if self._settings.get(url, None) is not None:
			self._settings.pop(url)
			self._flush_settings()
			self.changed.trigger(url)

	def _flush_settings(self):
		flush = getattr(self._settings, 'flush', None)
		if flush is not None:
			flush()

	def _validate_column_names(self, column_names):
		if isinstance(column_names, str):
			raise ValueError('Column names must be an iterable of names.')
		try:
			column_names = tuple(column_names)
		except TypeError:
			raise ValueError('Column names must be an iterable of names.') from None
		if any(not isinstance(column_name, str) for column_name in column_names):
			raise ValueError('Column names must be strings.')
		if len(column_names) != len(set(column_names)):
			raise ValueError('Column names must not contain duplicates.')
		registered_column_names = set(self._get_registered_column_names())
		for column_name in column_names:
			if column_name not in registered_column_names:
				raise ValueError('Column %r is not registered.' % column_name)
		return column_names

	def _get_available_columns(self, column_names):
		if not isinstance(column_names, (tuple, list)):
			return ()
		registered_column_names = set(self._get_registered_column_names())
		return tuple(
			column_name for column_name in column_names
			if isinstance(column_name, str) and column_name in registered_column_names
		)
