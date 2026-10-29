from fman.impl.localization import CatalogRegistry, resolve_locale
from fman.localization import (
	configure, register_plugin_catalog, translate, unregister_plugin_catalog,
)
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import json


def _write_catalog(directory, locale, values):
	Path(directory).mkdir(parents=True, exist_ok=True)
	with open(Path(directory) / (locale + '.json'), 'w', encoding='utf-8') as f:
		json.dump(values, f)


class ResolveLocaleTest(TestCase):
	def test_normalizes_saved_language_and_region(self):
		self.assertEqual('ru', resolve_locale(' RU_ru ', 'de-DE'))

	def test_normalizes_detected_language_when_no_override_exists(self):
		self.assertEqual('de', resolve_locale(None, 'de-DE'))
		self.assertEqual('fil', resolve_locale(None, 'fil-PH'))

	def test_uses_system_detection_when_saved_override_is_blank(self):
		self.assertEqual('ru', resolve_locale('  ', 'ru_RU'))

	def test_detects_system_language_when_no_override_exists(self):
		with patch(
			'fman.impl.localization.detect_system_language', return_value='de-DE'
		) as detect:
			self.assertEqual('de', resolve_locale(None))
		detect.assert_called_once_with(fallback='en')

	def test_uses_english_for_malformed_detection(self):
		self.assertEqual('en', resolve_locale(None, '123'))


class CatalogRegistryTest(TestCase):
	def test_plugin_catalog_is_isolated_and_falls_back_to_builtin_english(self):
		with TemporaryDirectory() as tmp:
			builtin = Path(tmp) / 'builtin'
			plugin_one = Path(tmp) / 'plugin-one'
			plugin_two = Path(tmp) / 'plugin-two'
			_write_catalog(builtin, 'en', {
				'menu': {'open': 'Open', 'close': 'Close', 'delete': 'Delete'},
			})
			_write_catalog(builtin, 'ru', {
				'menu': {'open': 'Открыть', 'close': 'Закрыть'},
			})
			_write_catalog(plugin_one, 'en', {
				'menu': {'open': 'Plugin one'},
			})
			_write_catalog(plugin_one, 'ru', {
				'menu': {'open': 'Первый'},
			})
			_write_catalog(plugin_two, 'en', {
				'menu': {'open': 'Plugin two'},
			})
			catalogs = CatalogRegistry('ru', builtin)
			catalogs.register_plugin('One', plugin_one)
			catalogs.register_plugin('Two', plugin_two)

			self.assertEqual('Первый', catalogs.t('menu.open', 'One'))
			self.assertEqual('Plugin two', catalogs.t('menu.open', 'Two'))
			self.assertEqual('Закрыть', catalogs.t('menu.close', 'One'))
			self.assertEqual('Delete', catalogs.t('menu.delete', 'One'))
			self.assertEqual('Открыть', catalogs.t('menu.open'))

	def test_plugin_catalog_must_be_explicitly_registered(self):
		with TemporaryDirectory() as tmp:
			builtin = Path(tmp) / 'builtin'
			plugin = Path(tmp) / 'plugin'
			_write_catalog(builtin, 'en', {'menu': {'open': 'Open'}})
			_write_catalog(plugin, 'en', {'menu': {'open': 'Plugin open'}})
			catalogs = CatalogRegistry('en', builtin)

			self.assertEqual('Open', catalogs.t('menu.open', 'Plugin'))

	def test_public_api_registers_only_plugins_with_translation_resources(self):
		with TemporaryDirectory() as tmp:
			builtin = Path(tmp) / 'builtin'
			plugin = Path(tmp) / 'plugin'
			_write_catalog(builtin, 'en', {'menu': {'open': 'Open'}})
			_write_catalog(plugin / 'Translations', 'en', {
				'menu': {'open': 'Plugin open'},
			})
			configure('en', builtin)
			try:
				self.assertFalse(register_plugin_catalog('NoCatalog', Path(tmp)))
				self.assertTrue(register_plugin_catalog('Plugin', plugin))
				self.assertEqual('Plugin open', translate('menu.open', 'Plugin'))
			finally:
				unregister_plugin_catalog('Plugin')

	def test_missing_key_falls_back_to_english_builtin_catalog(self):
		with TemporaryDirectory() as tmp:
			builtin = Path(tmp)
			_write_catalog(builtin, 'en', {'menu': {'close': 'Close'}})
			_write_catalog(builtin, 'ru', {'menu': {'open': 'Открыть'}})
			catalogs = CatalogRegistry('ru', builtin)

			self.assertEqual('Close', catalogs.t('menu.close'))
