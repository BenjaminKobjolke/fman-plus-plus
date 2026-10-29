from fman.impl.language import LanguageSettings
from fman.impl.util.settings import Settings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json


class LanguageSettingsTest(TestCase):
	def test_uses_detected_language_without_saved_override(self):
		with TemporaryDirectory() as directory:
			settings = Settings(str(Path(directory) / 'Settings.json'))
			languages = LanguageSettings(settings, directory)
			with patch(
				'fman.impl.localization.detect_system_language', return_value='de-DE'
			):
				self.assertEqual('de', languages.get_language())

	def test_saved_override_wins_and_is_persisted(self):
		with TemporaryDirectory() as directory:
			path = Path(directory) / 'Settings.json'
			settings = Settings(str(path))
			languages = LanguageSettings(settings, directory)
			languages.set_language('ru')
			self.assertEqual(
				'ru', LanguageSettings(Settings(str(path)), directory).get_language()
			)
			self.assertEqual({'language': 'ru'}, json.loads(path.read_text()))

	def test_system_choice_removes_saved_override(self):
		with TemporaryDirectory() as directory:
			path = Path(directory) / 'Settings.json'
			settings = Settings(str(path))
			languages = LanguageSettings(settings, directory)
			languages.set_language('ru')
			languages.set_language(None)
			self.assertNotIn('language', json.loads(path.read_text()))
			with patch(
				'fman.impl.localization.detect_system_language', return_value='de'
			):
				self.assertEqual('de', languages.get_language())

	def test_initializes_catalogs_for_the_resolved_language(self):
		with TemporaryDirectory() as directory:
			settings = Settings(str(Path(directory) / 'Settings.json'))
			languages = LanguageSettings(settings, directory)
			with patch(
				'fman.impl.localization.detect_system_language', return_value='ru-RU'
			), \
					patch('fman.impl.language.configure') as configure:
				self.assertEqual('ru', languages.initialize())
			configure.assert_called_once_with('ru', directory)
