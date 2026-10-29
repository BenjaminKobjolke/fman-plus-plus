"""Locale resolution and isolated built-in and plugin translation catalogs."""
from pathlib import Path
from re import compile as compile_regex

from python_localization import Localization as LanguageCatalog
from python_localization.detection import detect_system_language


_LANGUAGE_CODE = compile_regex(r'^[A-Za-z]{2,3}(?:[-_].*)?$')


def normalize_locale(locale: str | None) -> str | None:
	"""Return a normalized base language code, or None for an invalid value."""
	if not locale:
		return None
	locale = locale.strip()
	if not _LANGUAGE_CODE.fullmatch(locale):
		return None
	return locale.split('-', 1)[0].split('_', 1)[0].lower()


def resolve_locale(
	saved_locale: str | None,
	detected_locale: str | None = None,
) -> str:
	"""Use a saved language override, then the detected system language."""
	saved = normalize_locale(saved_locale)
	if saved:
		return saved
	if detected_locale is None:
		detected_locale = detect_system_language(fallback='en')
	return normalize_locale(detected_locale) or 'en'


def available_locales(catalog_dir: str | Path) -> list[str]:
	"""Return catalog languages with English first when it is available."""
	directory = Path(catalog_dir)
	languages = {path.stem.lower() for path in directory.glob('*.json')}
	languages.discard('en')
	return ['en'] + sorted(languages)


class CatalogRegistry:
	"""Look up a plugin's own catalog before built-in text and English fallback."""
	def __init__(self, locale: str, builtin_catalog_dir: str | Path):
		self._locale = normalize_locale(locale) or 'en'
		self._builtin = _Catalog(builtin_catalog_dir, self._locale)
		self._plugins: dict[str, _Catalog] = {}

	def register_plugin(self, plugin_name: str, catalog_dir: str | Path) -> bool:
		"""Register an opted-in plugin catalog directory, if it has JSON catalogs."""
		catalog_dir = Path(catalog_dir)
		if not catalog_dir.is_dir() or not any(catalog_dir.glob('*.json')):
			return False
		self._plugins[plugin_name] = _Catalog(catalog_dir, self._locale)
		return True

	def unregister_plugin(self, plugin_name: str) -> None:
		self._plugins.pop(plugin_name, None)

	def t(self, key: str, plugin_name: str | None = None) -> str:
		"""Translate `key`; plugin catalogs never see another plugin's text."""
		catalogs = []
		plugin = self._plugins.get(plugin_name) if plugin_name else None
		if plugin is not None:
			for language in dict.fromkeys((self._locale, 'en')):
				value = plugin.translate(key, language)
				if value is not None:
					return value
		catalogs.append(self._builtin)
		for catalog in catalogs:
			value = catalog.translate(key, self._locale)
			if value is not None:
				return value
		for catalog in catalogs:
			value = catalog.translate(key, 'en')
			if value is not None:
				return value
		return key


class _Catalog:
	"""Read one isolated catalog through python-localization."""
	def __init__(self, directory: str | Path, locale: str):
		self._directory = Path(directory)
		self._catalogs: dict[str, dict] = {}
		for language in dict.fromkeys((locale, 'en')):
			if not any(self._directory.glob(language + '.json')):
				continue
			catalog = LanguageCatalog(
				driver='json',
				lang_dir=str(self._directory),
				default_lang=language,
				fallback_lang='en',
			)
			self._catalogs[language] = catalog.get_all()

	def translate(self, key: str, language: str) -> str | None:
		value = self._catalogs.get(language)
		if value is None:
			return None
		for part in key.split('.'):
			if not isinstance(value, dict) or part not in value:
				return None
			value = value[part]
		return value if isinstance(value, str) else None
