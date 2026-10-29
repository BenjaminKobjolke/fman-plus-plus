"""Verify localization code and catalogs are available in fbs resources."""
from fman.impl.localization import CatalogRegistry
from importlib.util import find_spec
from pathlib import Path
from unittest import TestCase


RESOURCE_ROOT = Path(__file__).parents[4] / 'main' / 'resources' / 'base'
CATALOG_DIR = RESOURCE_ROOT / 'Plugins' / 'Core' / 'Translations'


class LocalizationPackagingTest(TestCase):
	def test_translation_modules_are_importable_by_the_freezer(self):
		self.assertIsNotNone(find_spec('fman.localization'))
		self.assertIsNotNone(find_spec('fman.impl.localization'))

	def test_catalogs_load_from_the_bundled_core_resource_layout(self):
		self.assertTrue((CATALOG_DIR / 'en.json').is_file())
		self.assertTrue((CATALOG_DIR / 'ru.json').is_file())
		catalogs = CatalogRegistry('ru', CATALOG_DIR)
		self.assertEqual('Удалить', catalogs.t('command_delete'))
