"""
One screen of a nested quicksearch menu: a list of string options, an action
per option and a way back. Screens are chained by constructing the next one
and calling show() from inside on_selected/on_cancelled - the child dialog
then opens only after the parent one has closed, which is what makes Escape
mean "back" rather than "cancel everything".

In its own module so that core.commands and core.keyword_editor can both use
it without importing each other.
"""
from core.quicksearch_matchers import contains_chars, \
	contains_chars_after_separator
from fman import QuicksearchItem, show_quicksearch

class QuicksearchScreen:

	_MATCHERS = (contains_chars_after_separator(' '), contains_chars)

	def show(self):
		options = list(self.get_options())
		choice = show_quicksearch(
			lambda q: self._filter_options(options, q), title=self.get_title()
		)
		if choice:
			option = choice[1]
			self.on_selected(option)
		else:
			self.on_cancelled()
	def get_title(self):
		return ''
	def get_options(self):
		raise NotImplementedError()
	def on_selected(self, option):
		raise NotImplementedError()
	def on_cancelled(self):
		pass
	def _filter_options(self, options, query):
		already_yielded = set()
		for matcher in self._MATCHERS:
			for option in options:
				match = matcher(option.lower(), query.lower())
				if match or not query:
					if option not in already_yielded:
						yield QuicksearchItem(option, highlight=match)
						already_yielded.add(option)
