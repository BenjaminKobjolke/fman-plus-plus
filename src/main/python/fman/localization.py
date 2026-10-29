"""Public translation functions for fman and opt-in plugin catalogs."""
from pathlib import Path

from fman.impl.localization import CatalogRegistry, resolve_locale
from fman.localization_keys import ENGLISH_TEXT, TEXT_KEYS


_registry: CatalogRegistry | None = None
_plugin_catalog_dirs: dict[str, Path] = {}


def configure(locale: str, builtin_catalog_dir: str | Path) -> None:
	"""Initialize translations before loading built-in and external plugins."""
	global _registry
	_registry = CatalogRegistry(locale, builtin_catalog_dir)
	for plugin_name, catalog_dir in _plugin_catalog_dirs.items():
		_registry.register_plugin(plugin_name, catalog_dir)


def register_plugin_catalog(plugin_name: str, plugin_dir: str | Path) -> bool:
	"""Opt in when a plugin ships a Translations directory with JSON catalogs."""
	catalog_dir = Path(plugin_dir) / 'Translations'
	if not catalog_dir.is_dir() or not any(catalog_dir.glob('*.json')):
		return False
	_plugin_catalog_dirs[plugin_name] = catalog_dir
	if _registry is not None:
		return _registry.register_plugin(plugin_name, catalog_dir)
	return True


def unregister_plugin_catalog(plugin_name: str) -> None:
	_plugin_catalog_dirs.pop(plugin_name, None)
	if _registry is not None:
		_registry.unregister_plugin(plugin_name)


def translate(key: str, plugin_name: str | None = None) -> str:
	"""Translate built-in text or text scoped to an opted-in plugin."""
	if _registry is None:
		return ENGLISH_TEXT.get(key, key)
	return _registry.t(key, plugin_name)


def translate_text(text: str) -> str:
	"""Translate a known built-in English string at a shared UI boundary."""
	key = TEXT_KEYS.get(text)
	return translate(key) if key else text


__all__ = [
	'configure', 'register_plugin_catalog', 'resolve_locale',
	'translate_text',
	'translate', 'unregister_plugin_catalog',
]
