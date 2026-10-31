from core.commands.util import get_user, get_well_known_dirs, is_hidden
from core.suggest_locations import SuggestLocations
from fman import DirectoryPaneCommand, show_quicksearch, PLATFORM, load_json, \
	DirectoryPaneListener, is_incognito
from fman.fs import exists, resolve
from fman.url import as_url, splitscheme, as_human_readable
from itertools import islice
from os.path import expanduser, expandvars, islink
from pathlib import Path, PurePath
from random import shuffle
from time import time

import os
import re
import sys

__all__ = ['GoTo', 'GoToListener']

class GoTo(DirectoryPaneCommand):
	def __call__(self, query=''):
		visited_paths = self._get_visited_paths()
		get_items = SuggestLocations(
			_with_well_known_dirs(visited_paths), labels=get_well_known_dirs()
		)
		result = show_quicksearch(get_items, self._get_tab_completion, query)
		if result:
			url = self._get_target_location(*result)
			if exists(url):
				# Use OpenDirectory because it handles errors gracefully:
				self.pane.run_command('open_directory', {'url': url})
			elif PLATFORM == 'Windows':
				from core.commands.network_shares import ShareLogin, log_in_to_share
				result = log_in_to_share(url)
				if result == ShareLogin.CONNECTED and exists(url):
					self.pane.run_command('open_directory', {'url': url})
				elif result == ShareLogin.NOT_A_SHARE:
					path = as_human_readable(url)
					_remove_from_visited_paths(visited_paths, path)
			else:
				path = as_human_readable(url)
				_remove_from_visited_paths(visited_paths, path)
	def _get_target_location(self, query, suggested_dir):
		if suggested_dir:
			# The suggested_dir is for instance set when the user clicks on it
			# with the mouse. If set, it always takes precedence. So return it:
			return as_url(suggested_dir)
		if PLATFORM == 'Windows':
			from core.fs.local.windows.shares import parse_share_address
			address = parse_share_address(query)
			if address is not None:
				return address.as_fman_url()
		url = as_url(expandvars(expanduser(query.rstrip())))
		if PLATFORM == 'Windows' and re.match(r'\\[^\\]', query):
			# Resolve '\Some\dir' to 'C:\Some\dir'.
			try:
				url = resolve(url)
			except OSError:
				pass
		return url
	def _get_tab_completion(self, query, curr_item):
		if curr_item:
			result = curr_item.title
			if not result.endswith(os.sep):
				result += os.sep
			return result
	def _get_visited_paths(self):
		# TODO: Rename to Visited Locations.json?
		result = load_json('Visited Paths.json', default={})
		# Check for length 2 because the directories in which fman opens are
		# already in Visited Paths:
		if len(result) <= 2:
			result.update({
				path: 0 for path in self._get_default_paths()
			})
		return result
	def _get_default_paths(self, exclude={'/proc', '/run', '/sys'}):
		home_dir = expanduser('~')
		result = set(self._get_nonhidden_subdirs(home_dir))
		# Add directories in C:\ on Windows, or / on Unix:
		try:
			children = Path(PurePath(sys.executable).anchor).iterdir()
		except OSError:
			pass
		else:
			for child in children:
				if str(child) in exclude:
					continue
				try:
					if child.is_dir():
						try:
							next(iter(child.iterdir()))
						except StopIteration:
							pass
						else:
							result.add(str(child))
				except OSError:
					pass
		if PLATFORM == 'Linux':
			media_user = os.path.join('/media', get_user())
			if os.path.exists(media_user):
				result.add(media_user)
			# We need to add more suggestions on Linux, because unlike Windows
			# and Mac, we (currently) do not integrate with the OS's native
			# search functionality:
			result.update(islice(self._traverse_by_mtime(home_dir), 500))
			result.update(
				islice(self._traverse_by_mtime('/', exclude=exclude), 500)
			)
		return result
	def _get_nonhidden_subdirs(self, dir_path):
		for file_name in os.listdir(dir_path):
			file_path = os.path.join(dir_path, file_name)
			if os.path.isdir(file_path) and not is_hidden(file_path):
				yield os.path.join(dir_path, file_name)
	def _traverse_by_mtime(self, dir_path, exclude=None):
		if exclude is None:
			exclude = set()
		to_visit = [(os.stat(dir_path), dir_path)]
		already_yielded = set()
		while to_visit:
			stat, parent = to_visit.pop()
			if parent in exclude:
				continue
			yield parent
			try:
				parent_contents = os.listdir(parent)
			except OSError:
				continue
			for file_name in parent_contents:
				if file_name.startswith('.'):
					continue
				file_path = os.path.join(parent, file_name)
				try:
					if not os.path.isdir(file_path) or islink(file_path):
						continue
				except OSError:
					continue
				try:
					stat = os.stat(file_path)
				except OSError:
					pass
				else:
					already_yielded.add(stat.st_ino)
					to_visit.append((stat, file_path))
			to_visit.sort(key=lambda tpl: tpl[0].st_mtime)

class GoToListener(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.is_first_path_change = True
	def on_path_changed(self):
		if self.is_first_path_change:
			# on_path_changed() is also called when fman starts. Since this is
			# not a user-initiated path change, we don't want to count it:
			self.is_first_path_change = False
			return
		if is_incognito():
			return
		url = self.pane.get_path()
		scheme, path = splitscheme(url)
		if scheme != 'file://':
			return
		visited_paths = \
			load_json('Visited Paths.json', default={}, save_on_quit=True)
		# Ensure we're using backslashes \ on Windows:
		path = as_human_readable(url)
		visited_paths[path] = visited_paths.get(path, 0) + 1
		if len(visited_paths) > 500:
			_shrink_visited_paths(visited_paths, 250)
		else:
			# Spend a little time cleaning up outdated paths. This method is
			# called asynchronously, so no problem performing some work here.
			_remove_nonexistent(visited_paths, timeout_secs=0.01)

def _with_well_known_dirs(visited_paths):
	# Home, Desktop, Documents and Downloads stay suggestable forever, not just
	# while _get_default_paths() below still seeds them: that branch is dead
	# after the first run, and _shrink_visited_paths drops whatever you stopped
	# visiting.
	#
	# A *copy*, because load_json caches by name and hands back the same dict
	# object every time (fman/impl/plugins/config.py), and GoToListener loads it
	# with save_on_quit=True - adding to it in place would write these
	# suggestions into the user's real Visited Paths.json.
	result = dict(visited_paths)
	for path in get_well_known_dirs():
		# Skip what this machine doesn't have, rather than offer a row that
		# fails on Enter:
		if os.path.isdir(path):
			result.setdefault(path, 0)
	return result

def _shrink_visited_paths(vps, size):
	paths_per_count = {}
	for p, count in vps.items():
		paths_per_count.setdefault(count, []).append(p)
	count_paths = sorted(paths_per_count.items())
	# Remove least frequently visited paths until we reach the desired size:
	while len(vps) > size:
		count, paths = count_paths[0]
		del vps[paths.pop()]
		if not paths:
			count_paths = count_paths[1:]
	# Re-scale those paths that are left. This gives more recent paths a chance
	# to rise to the top. Eg. {'a': 1000, 'b': 1} -> {'a': 2, 'b': 1}.
	for i, (count, paths) in enumerate(count_paths):
		for p in paths:
			vps[p] = i + 1

def _remove_nonexistent(vps, timeout_secs):
	# Randomly check visited paths for existence, until the timeout expires.
	# Choose all elts. with equal probability. It's tempting to be more clever
	# and use the visit counts somehow. But it's not clear this will be better:
	# Higher counts may indicate that a directory is "stable" and doesn't change
	# often. On the other hand, they also appear in search results more often,
	# hence incur a higher "penalty" when we get it wrong. So keep it simple.
	end_time = time() + timeout_secs
	paths = list(vps)
	shuffle(paths)
	for path in paths:
		if time() >= end_time:
			break
		try:
			is_dir = os.path.isdir(path)
		except OSError:
			continue
		if not is_dir:
			_remove_from_visited_paths(vps, path)

def _remove_from_visited_paths(vps, path):
	for p in list(vps):
		if p == path or p.startswith(path + os.sep):
			try:
				del vps[p]
			except KeyError:
				pass
