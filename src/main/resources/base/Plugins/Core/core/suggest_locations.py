"""Go To folder suggestion implementation."""

from core.quicksearch_matchers import path_starts_with, basename_starts_with, \
	contains_substring, contains_chars
from fman import PLATFORM, QuicksearchItem
from itertools import islice, chain
from os.path import expanduser, isabs, normpath
from pathlib import Path

import os
import re

if PLATFORM == 'Mac':
	from fman.impl.mac import get_core_services


def unexpand_user(path, expanduser_=expanduser):
	home_dir = expanduser_('~')
	if path.startswith(home_dir):
		path = '~' + path[len(home_dir):]
	return path

class SuggestLocations:

	_MATCHERS = (
		path_starts_with, basename_starts_with, contains_substring,
		contains_chars
	)

	class LocalFileSystem:
		def isdir(self, path):
			return os.path.isdir(path)
		def expanduser(self, path):
			return expanduser(path)
		def listdir(self, path):
			return os.listdir(path)
		def resolve(self, path):
			return str(Path(path).resolve())
		def samefile(self, f1, f2):
			return os.path.samefile(f1, f2)
		def find_folders_starting_with(self, pattern, timeout_secs=0.02):
			if PLATFORM == 'Mac':
				ns = get_core_services()
				pred = ns['NSPredicate'].predicateWithFormat_argumentArray_(
					"kMDItemContentType == 'public.folder' && "
					"kMDItemFSName BEGINSWITH[c] %@", [pattern]
				)
				query = ns['NSMetadataQuery'].alloc().init()
				query.setPredicate_(pred)
				query.setSearchScopes_(ns['NSArray'].arrayWithObject_('/'))
				query.startQuery()
				ns['NSRunLoop'].currentRunLoop().runUntilDate_(
					ns['NSDate'].dateWithTimeIntervalSinceNow_(timeout_secs)
				)
				query.stopQuery()
				for item in query.results():
					yield item.valueForAttribute_("kMDItemPath")
			elif PLATFORM == 'Windows':
				import adodbapi
				from pythoncom import com_error
				try:
					conn = adodbapi.connect(
						"Provider=Search.CollatorDSO;"
						"Extended Properties='Application=Windows';"
					)
					cursor = conn.cursor()

					# adodbapi claims to support "paramstyles", which would let us
					# pass parameters as an extra arg to .execute(...), without
					# having to worry about escaping them. Alas, adodbapi raises an
					# error when this feature is used. We thus have to escape the
					# param ourselves:
					def escape(param):
						return re.subn(r'([%_\[\]\^])', r'[\1]', param)[0]

					cursor.execute(
						"SELECT TOP 5 System.ItemPathDisplay FROM SYSTEMINDEX "
						"WHERE "
						"System.ItemType = 'Directory' AND "
						"System.ItemNameDisplay LIKE %r "
						"ORDER BY System.ItemPathDisplay"
						% (escape(pattern) + '%')
					)
					for row in iter(cursor.fetchone, None):
						value = row['System.ItemPathDisplay']
						# Seems to be None sometimes:
						if value:
							yield value
				except (adodbapi.Error, com_error):
					pass

	def __init__(self, visited_paths, file_system=None, labels=None):
		if file_system is None:
			# Encapsulating filesystem-related functionality in a separate field
			# allows us to use a different implementation for testing.
			file_system = self.LocalFileSystem()
		self.visited_paths = visited_paths
		self.fs = file_system
		# A longer name-prefix query cannot match after a prefix found no folders.
		self._prefixes_without_folders = []
		# {path: name} for directories that have a name of their own, such as
		# 'Home' for ~. Both searchable and shown as a hint - see
		# _filter_matching.
		self.labels = labels or {}
	def __call__(self, query):
		possible_dirs = self._gather_dirs(query)
		return self._filter_matching(possible_dirs, query)
	def _gather_dirs(self, query):
		path = self._normalize_query(query)
		if isabs(path):
			if self._is_existing_dir(path):
				try:
					dir_ = self.fs.resolve(path)
				except OSError:
					dir_ = path
				return [dir_] + self._gather_subdirs(dir_)
			else:
				parent_path = os.path.dirname(path)
				if self._is_existing_dir(parent_path):
					try:
						parent = self.fs.resolve(parent_path)
					except OSError:
						pass
					else:
						return self._gather_subdirs(parent)
		result = set(self.visited_paths)
		if len(query) > 2:
			"""Compensate for directories not yet in self.visited_paths:"""
			prefix = query.lower()
			if not any(prefix.startswith(p) for p in self._prefixes_without_folders):
				fs_folders = list(islice(
					self.fs.find_folders_starting_with(query), 100
				))
				if not fs_folders:
					self._prefixes_without_folders.append(prefix)
				result.update(self._sorted(fs_folders)[:10])
		return self._sorted(result)
	def _normalize_query(self, query):
		result = normpath(self.fs.expanduser(query))
		if PLATFORM == 'Windows':
			# Windows completely ignores trailing spaces in directory names at
			# all times. Make our implementation reflect this:
			result = result.rstrip(' ')
			# Handle the case where the user has entered a drive such as 'E:'
			# without the trailing backslash:
			if re.match(r'^[A-Z]:$', result):
				result += '\\'
		return result
	def _sorted(self, dirs):
		return sorted(dirs, key=lambda dir_: (
			-self.visited_paths.get(dir_, 0), len(dir_), dir_.lower()
		))
	def _is_existing_dir(self, path):
		try:
			return self.fs.isdir(path)
		except OSError:
			return False
	def _filter_matching(self, dirs, query):
		use_tilde = \
			not query.startswith(os.path.dirname(self.fs.expanduser('~')))
		has_parent_segment = '..' in re.split(r'[\\/]+', query)
		matching_query = query
		if has_parent_segment:
			normalized_query = self._normalize_query(query)
			matching_query = self._unexpand_user(normalized_query) \
				if use_tilde else normalized_query
		matchers = self._MATCHERS[:1] if has_parent_segment else self._MATCHERS
		result = [[] for _ in self._MATCHERS]
		for dir_ in dirs:
			title = self._unexpand_user(dir_) if use_tilde else dir_
			label = self.labels.get(dir_, '')
			for i, matcher in enumerate(matchers):
				match = matcher(title.lower(), matching_query.lower())
				if match is not None:
					result[i].append(QuicksearchItem(
						dir_, title, highlight=match, hint=label
					))
					break
			else:
				# The path did not match, but the name might: the home
				# directory shows as '~', which contains none of the letters in
				# 'home'. Ranked by the same matchers, so an exact name hit
				# still beats a loose path hit. Nothing in the title to
				# highlight, as with a command-palette keyword match.
				for i, matcher in enumerate(matchers):
					if label and matcher(label.lower(), matching_query.lower()) \
							is not None:
						result[i].append(QuicksearchItem(dir_, title, hint=label))
						break
		return list(chain.from_iterable(result))
	def _gather_subdirs(self, dir_):
		result = []
		try:
			dir_contents = self.fs.listdir(dir_)
		except OSError:
			pass
		else:
			for name in dir_contents:
				file_path = os.path.join(dir_, name)
				try:
					if self.fs.isdir(file_path):
						result.append(file_path)
				except OSError:
					pass
		return self._sorted(result)
	def _unexpand_user(self, path):
		return unexpand_user(path, self.fs.expanduser)
