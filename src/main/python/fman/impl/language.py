"""Persist the app language preference and initialize its catalogs."""
from fman.impl.localization import (
	available_locales, normalize_locale, resolve_locale,
)
from fman.localization import configure


LANGUAGE_SETTING = 'language'


class LanguageSettings:
	"""Resolve the app override and persist language picker choices."""
	def __init__(self, settings, catalog_dir):
		self._settings = settings
		self._catalog_dir = catalog_dir
	def get_override(self):
		return normalize_locale(self._settings.get(LANGUAGE_SETTING, None))
	def get_language(self):
		return resolve_locale(self.get_override())
	def get_languages(self):
		return available_locales(self._catalog_dir)
	def set_language(self, locale):
		if locale is None:
			self._settings.pop(LANGUAGE_SETTING)
		else:
			locale = normalize_locale(locale)
			if locale is None:
				raise ValueError('Invalid language code.')
			self._settings[LANGUAGE_SETTING] = locale
		self._settings.flush()
	def initialize(self):
		locale = self.get_language()
		configure(locale, self._catalog_dir)
		return locale
