from itertools import chain
from os.path import basename

import os

def matched_in_order(matchers, entries, query, make_item):
	"""
	`entries` - (text, value) pairs - as rows, best matches first: one bucket
	per matcher, in the order given, and within a bucket the order `entries`
	came in. An entry lands in the bucket of the FIRST matcher that hits it,
	so a loose matcher never outranks a strict one on the same entry.
	Unmatched entries are dropped. `make_item(value, text, highlight)` builds
	the row - usually a QuicksearchItem, which this module deliberately does
	not import.
	"""
	buckets = [[] for _ in matchers]
	for text, value in entries:
		for i, matcher in enumerate(matchers):
			highlight = matcher(text.lower(), query.lower())
			if highlight is not None:
				buckets[i].append(make_item(value, text, highlight))
				break
	return list(chain.from_iterable(buckets))


def path_starts_with(path, query):
	# We do want to return ~/Downloads when query is ~/Downloads/:
	query = query.rstrip(os.sep)
	if path.lower().startswith(query.lower()):
		return list(range(len(query)))

def basename_starts_with(path, query):
	name = basename(path.lower())
	if name.startswith(query.lower()):
		offset = len(path) - len(name)
		return [i + offset for i in range(len(query))]

def contains_chars(text, query):
	indices = []
	i = 0
	for char in query:
		try:
			i += text[i:].index(char)
		except ValueError:
			return None
		indices.append(i)
		i += 1
	return indices

def contains_chars_any_order(text, query):
	# Like contains_chars, but each space-separated word is matched
	# independently, so word order in the query does not matter:
	# 'panes show' finds 'show all panes'.
	return _every_word(contains_chars, text, query)

def contains_words(text, query):
	# Every space-separated word must appear as a substring, in any order:
	# 'pdf ryd' finds 'ryd/invoice.pdf'.
	return _every_word(contains_substring, text, query)

def _every_word(matcher, text, query):
	words = query.split()
	if not words:
		return None
	matched = set()
	for word in words:
		indices = matcher(text, word)
		if indices is None:
			return None
		matched.update(indices)
	return sorted(matched)

def basename_contains_chars(path, query):
	# Loose letters in the last path segment only, and only for a one-word
	# query: over a whole path, or word by word, loose letters match almost
	# any long file name. Several words are matched by contains_words.
	if len(query.split()) != 1:
		return None
	name = basename(path)
	indices = contains_chars(name, query.strip())
	if indices is None:
		return None
	offset = len(path) - len(name)
	return [i + offset for i in indices]

def contains_substring(text, query):
	try:
		start = text.index(query)
	except ValueError:
		return None
	return list(range(start, start + len(query)))

def contains_chars_after_separator(separator):
	def result(text, query):
		result_ = []
		skip_to_next_part = False
		for i, char in enumerate(text):
			if skip_to_next_part:
				if char == separator:
					skip_to_next_part = False
				continue
			if not query:
				break
			if char == query[0]:
				result_.append(i)
				query = query[1:]
			else:
				skip_to_next_part = char != separator
		if query:
			return None
		return result_
	return result
def match_titles_or_keywords(matchers, titles, keywords, query):
	"""
	How the command palettes rank one entry against `query`: (bucket, index,
	highlight) - `index` being the position in `titles` of the name that titles
	the row, and `bucket` its rank, lower being better. None if nothing matches.

	Bucket 0 is exactness: a title or a hidden keyword that *equals* the query.
	Then come the `matchers`, one bucket each, applied to the titles. Last is a
	single bucket for loose keyword hits. Exactness ranks first because an exact
	synonym is a better answer than the loosest possible name match: `exit` finds
	Quit (its keyword) before Extract to opposite (a mid-word subsequence of its
	name). Among non-exact matches, names still beat keywords.

	A keyword hit - exact or loose - keeps the command's first name and gets no
	highlight, since the typed characters are not in that name. `titles`,
	`keywords` and `query` are lowercase.
	"""
	if query:
		for index, title in enumerate(titles):
			if title == query:
				return 0, index, list(range(len(query)))
		if query in keywords:
			return 0, 0, []
	for index, title in enumerate(titles):
		for bucket, matcher in enumerate(matchers):
			highlight = matcher(title, query)
			if highlight is not None:
				return bucket + 1, index, highlight
	for keyword in keywords:
		for matcher in matchers:
			if matcher(keyword, query) is not None:
				return bucket_count(matchers) - 1, 0, []
	return None

def bucket_count(matchers):
	"""
	How many buckets match_titles_or_keywords can return for `matchers`, so its
	callers can size their result lists without hard-coding the offsets.
	"""
	# One per matcher, plus the exact bucket in front and the loose-keyword one
	# at the back.
	return len(matchers) + 2
