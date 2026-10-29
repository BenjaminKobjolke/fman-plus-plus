"""Tests for the shipped built-in translation catalogs."""
from fman import translate
from fman.impl.localization import CatalogRegistry
from fman.localization import (
	configure, register_plugin_catalog, translate_text,
	unregister_plugin_catalog,
)
from fman.localization_keys import ALL_KEYS, ENGLISH_TEXT
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import json


def _write_catalog(directory, locale, values):
	Path(directory).mkdir(parents=True, exist_ok=True)
	with open(Path(directory) / (locale + '.json'), 'w', encoding='utf-8') as f:
		json.dump(values, f)


CATALOG_DIR = Path(__file__).parents[4] / 'main' / 'resources' / 'base' \
	/ 'Plugins' / 'Core' / 'Translations'


class BuiltinCatalogTest(TestCase):
	def test_english_and_russian_catalogs_define_every_builtin_key(self):
		russian = CatalogRegistry('ru', CATALOG_DIR)
		english = CatalogRegistry('en', CATALOG_DIR)
		for key in ALL_KEYS:
			with self.subTest(key=key):
				self.assertEqual(ENGLISH_TEXT[key], english.t(key))
				self.assertNotEqual(key, russian.t(key))
				self.assertNotEqual(english.t(key), russian.t(key))

	def test_unknown_key_is_returned_as_is(self):
		registry = CatalogRegistry('ru', CATALOG_DIR)
		self.assertEqual('missing.key', registry.t('missing.key'))

	def test_known_builtin_command_title_is_translated(self):
		configure('ru', CATALOG_DIR)
		try:
			self.assertEqual('Удалить', translate_text('Delete'))
		finally:
			configure('en', CATALOG_DIR)

	def test_public_plugin_translation_uses_opted_in_catalog_and_english_fallback(self):
		with TemporaryDirectory() as tmp:
			plugin_dir = Path(tmp) / 'My Plugin'
			_write_catalog(plugin_dir / 'Translations', 'en', {
				'menu': {'open': 'Plugin open', 'close': 'Plugin close'},
			})
			_write_catalog(plugin_dir / 'Translations', 'ru', {
				'menu': {'open': 'Открыть'},
			})
			configure('ru', CATALOG_DIR)
			try:
				self.assertTrue(
					register_plugin_catalog('My Plugin', plugin_dir)
				)
				self.assertEqual(
					'Открыть', translate('menu.open', 'My Plugin')
				)
				self.assertEqual(
					'Plugin close', translate('menu.close', 'My Plugin')
				)
			finally:
				unregister_plugin_catalog('My Plugin')
				configure('en', CATALOG_DIR)
