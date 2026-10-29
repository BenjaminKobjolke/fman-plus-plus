from core.commands.language import (
	SYSTEM_LANGUAGE, ChangeLanguage, get_language_items,
)
from unittest import TestCase
from unittest.mock import patch


class GetLanguageItemsTest(TestCase):
	def test_system_choice_precedes_available_languages(self):
		items = get_language_items(['en', 'ru'], None, '')
		self.assertEqual(
			[SYSTEM_LANGUAGE, 'en', 'ru'], [item.value for item in items]
		)
	def test_marks_the_current_choice(self):
		items = get_language_items(['en', 'ru'], 'ru', '')
		hints = {item.value: item.hint for item in items}
		self.assertEqual('current', hints['ru'])
		self.assertEqual('', hints['en'])
	def test_filters_choices(self):
		items = get_language_items(['en', 'ru'], None, 'rus')
		self.assertEqual(['ru'], [item.value for item in items])


class ChangeLanguageTest(TestCase):
	def test_saves_selection_and_prompts_for_restart(self):
		command = ChangeLanguage(None)
		with patch('core.commands.language.get_languages', return_value=['en', 'ru']), \
				patch('core.commands.language.get_language', return_value=None), \
				patch('core.commands.language.set_language') as set_language, \
				patch(
					'core.commands.language.show_quicksearch', return_value=(0, 'ru')
				), \
				patch('core.commands.language.show_alert') as show_alert:
			command()
		set_language.assert_called_once_with('ru')
		show_alert.assert_called_once()
		self.assertIn('restart', show_alert.call_args.args[0].lower())
	def test_does_nothing_when_picker_is_cancelled(self):
		command = ChangeLanguage(None)
		with patch('core.commands.language.get_languages', return_value=['en']), \
				patch('core.commands.language.get_language', return_value=None), \
				patch('core.commands.language.set_language') as set_language, \
				patch('core.commands.language.show_quicksearch', return_value=None), \
				patch('core.commands.language.show_alert') as show_alert:
			command()
		set_language.assert_not_called()
		show_alert.assert_not_called()
	def test_system_choice_clears_override(self):
		command = ChangeLanguage(None)
		with patch('core.commands.language.get_languages', return_value=['en']), \
				patch('core.commands.language.get_language', return_value='en'), \
				patch('core.commands.language.set_language') as set_language, \
				patch(
					'core.commands.language.show_quicksearch', return_value=(0, None)
				), \
				patch('core.commands.language.show_alert'):
			command()
		set_language.assert_called_once_with(None)
