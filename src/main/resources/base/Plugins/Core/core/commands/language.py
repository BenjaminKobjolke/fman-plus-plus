"""Choose a built-in language and save it for the next fman start."""
from core.quicksearch_matchers import contains_chars_after_separator, \
	contains_chars, matched_in_order
from fman import ApplicationCommand, QuicksearchItem, get_language, \
	get_languages, set_language, show_alert, show_quicksearch, translate
from fman.localization_keys import LANGUAGE_CURRENT, LANGUAGE_ENGLISH, \
	LANGUAGE_RESTART, LANGUAGE_RUSSIAN, SYSTEM_LANGUAGE as SYSTEM_LANGUAGE_KEY


SYSTEM_LANGUAGE = None
_LANGUAGE_NAMES = {
	'en': LANGUAGE_ENGLISH,
	'ru': LANGUAGE_RUSSIAN,
}
_MATCHERS = (contains_chars_after_separator(' '), contains_chars)


def get_language_items(languages, current, query):
	"""Build the filtered language list with the active choice marked."""
	entries = [(SYSTEM_LANGUAGE, SYSTEM_LANGUAGE_KEY)]
	entries.extend(
		(locale, _LANGUAGE_NAMES.get(locale, locale))
		for locale in languages
	)
	return matched_in_order(
		_MATCHERS, [
			(translate(label) if label in _LANGUAGE_NAMES.values() or
				label == SYSTEM_LANGUAGE_KEY else label, value)
			for value, label in entries
		], query,
		lambda value, label, highlight: QuicksearchItem(
			value, label, highlight,
			hint=translate(LANGUAGE_CURRENT) if value == current else ''
		)
	)


class ChangeLanguage(ApplicationCommand):
	aliases = ('Change language',)
	def __call__(self):
		languages = get_languages()
		current = get_language()
		choices = [SYSTEM_LANGUAGE] + languages
		item = choices.index(current) if current in choices else 0
		result = show_quicksearch(
			lambda query: get_language_items(languages, current, query),
			item=item
		)
		if not result or result[1] == current:
			return
		set_language(result[1])
		show_alert(translate(LANGUAGE_RESTART))


__all__ = ['ChangeLanguage', 'get_language_items']
