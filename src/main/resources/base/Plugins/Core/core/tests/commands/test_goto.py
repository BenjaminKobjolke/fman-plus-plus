from core.commands.goto import _shrink_visited_paths, _with_well_known_dirs, \
	GoTo, GoToListener
from core.suggest_locations import SuggestLocations
from core.util import filenotfounderror
from fman import PLATFORM
from fman.impl import incognito
from fman.url import as_human_readable, as_url
from os.path import normpath
from unittest import TestCase, skipIf
from unittest.mock import patch, Mock

import os


@skipIf(PLATFORM != 'Windows', 'SMB addresses only exist on Windows')
class GoToShareTest(TestCase):
	def test_smb_share_and_server_addresses_resolve(self):
		command = GoTo(Mock())
		self.assertEqual(
			as_url(r'\\srv\share\a'),
			command._get_target_location('smb://srv/share/a', None)
		)
		self.assertEqual(
			'network://srv', command._get_target_location('smb://srv', None)
		)

	def test_cancelled_login_keeps_path_in_visited_paths(self):
		from core.commands.network_shares import ShareLogin

		visited = {'\\\\server\\share': 1}
		pane = Mock()
		command = GoTo(pane)
		with patch.object(command, '_get_visited_paths', return_value=visited), \
				patch('core.commands.goto.SuggestLocations'), \
				patch(
					'core.commands.goto.show_quicksearch',
					return_value=('smb://server/share', None)
				), \
				patch('core.commands.goto.exists', return_value=False), \
				patch(
					'core.commands.network_shares.log_in_to_share',
					return_value=ShareLogin.CANCELLED
				), \
				patch('core.commands.goto._remove_from_visited_paths') as remove:
			command()
		remove.assert_not_called()
		pane.run_command.assert_not_called()


class GoToListenerIncognitoTest(TestCase):
	def setUp(self):
		self.addCleanup(incognito.set_incognito, False)
		self.listener = GoToListener(Mock(spec=['get_path']))
		self.listener.is_first_path_change = False
		self.listener.pane.get_path.return_value = 'file:///visited/folder'

	def test_does_not_count_visits_while_incognito(self):
		incognito.set_incognito(True)

		with patch('core.commands.goto.load_json') as load_json:
			self.listener.on_path_changed()

		load_json.assert_not_called()

	def test_ignores_initial_path_change_before_checking_incognito(self):
		incognito.set_incognito(True)
		self.listener.is_first_path_change = True

		with patch('core.commands.goto.load_json') as load_json:
			self.listener.on_path_changed()

		self.assertFalse(self.listener.is_first_path_change)
		load_json.assert_not_called()

	def test_counts_visits_when_incognito_is_off(self):
		incognito.set_incognito(False)
		visited_paths = {}

		with patch(
				'core.commands.goto.load_json',
				return_value=visited_paths) as load_json:
			with patch('core.commands.goto._remove_nonexistent'):
				self.listener.on_path_changed()

		load_json.assert_called_once_with(
			'Visited Paths.json', default={}, save_on_quit=True)
		path = as_human_readable(self.listener.pane.get_path())
		self.assertEqual(1, visited_paths[path])

class ShrinkVisiblePathsTest(TestCase):
	def test_basic(self):
		vps = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}
		_shrink_visited_paths(vps, 3)
		self.assertEqual({'c': 1, 'd': 2, 'e': 3}, vps)
	def test_multiple_similar(self):
		vps = {'a': 1, 'b': 1, 'c': 3, 'd': 3, 'e': 5}
		_shrink_visited_paths(vps, 3)
		self.assertEqual({'c': 1, 'd': 1, 'e': 2}, vps)

class WithWellKnownDirsTest(TestCase):

	_HOME = os.path.join('C:\\', 'home')
	_DESKTOP = os.path.join('C:\\', 'home', 'Desktop')
	_DIRS = [_HOME, _DESKTOP]

	def test_adds_them_without_touching_the_original(self):
		vps = {self._HOME: 7, 'elsewhere': 3}
		with patch('core.commands.goto.get_well_known_dirs', lambda: self._DIRS), \
			 patch('core.commands.goto.os.path.isdir', lambda p: True):
			result = _with_well_known_dirs(vps)
		# A visited directory keeps its count - otherwise adding the defaults
		# would demote the user's most-used directory to the bottom:
		self.assertEqual({self._HOME: 7, 'elsewhere': 3, self._DESKTOP: 0}, result)
		# The caller's dict is the one load_json caches and GoToListener saves
		# on quit, so it must come back untouched:
		self.assertEqual({self._HOME: 7, 'elsewhere': 3}, vps)
	def test_skips_what_isnt_a_directory(self):
		with patch('core.commands.goto.get_well_known_dirs', lambda: self._DIRS), \
			 patch('core.commands.goto.os.path.isdir', lambda p: p == self._HOME):
			result = _with_well_known_dirs({})
		self.assertEqual({self._HOME: 0}, result)

class SuggestLocationsTest(TestCase):

	class StubLocalFileSystem:
		def __init__(self, files, home_dir):
			self.files = files
			self.home_dir = home_dir
			self.queried_prefixes = []
		def isdir(self, path):
			if PLATFORM == 'Windows' and path.endswith(' '):
				# Strange behaviour on Windows: isdir('X ') returns True if X
				# (without space) exists.
				path = path.rstrip(' ')
			try:
				self._get_dir(path)
			except KeyError:
				return False
			return True
		def _get_dir(self, path):
			if not path:
				raise KeyError(path)
			path = normpath(path)
			parts = path.split(os.sep) if path != os.sep else ['']
			if len(parts) > 1 and parts[-1] == '':
				parts = parts[:-1]
			curr = self.files
			for part in parts:
				for file_name, items in curr.items():
					if self._normcase(file_name) == self._normcase(part):
						curr = items
						break
				else:
					raise KeyError(part)
			return curr
		def expanduser(self, path):
			return path.replace('~', self.home_dir)
		def listdir(self, path):
			try:
				return sorted(list(self._get_dir(path)))
			except KeyError as e:
				raise filenotfounderror(path) from e
		def resolve(self, path):
			is_case_sensitive = PLATFORM == 'Linux'
			if is_case_sensitive:
				return path
			dir_ = os.path.dirname(path)
			if dir_ == path:
				# We're at the root of the file system.
				return path
			dir_ = self.resolve(dir_)
			try:
				dir_contents = self.listdir(dir_)
			except OSError:
				matching_names = []
			else:
				matching_names = [
					f for f in dir_contents
					if f.lower() == os.path.basename(path).lower()
				]
			if not matching_names:
				return path
			return os.path.join(dir_, matching_names[0])
		def samefile(self, f1, f2):
			return self._get_dir(f1) == self._get_dir(f2)
		def find_folders_starting_with(self, prefix):
			self.queried_prefixes.append(prefix)
			return list(
				self._find_folders_recursive(self.files, prefix.lower()))
		def _find_folders_recursive(self, files, prefix):
			for f, subfiles in files.items():
				if f.lower().startswith(prefix):
					yield f
				for sub_f in self._find_folders_recursive(subfiles, prefix):
					# We don't use join(...) here because of the case f=''. We
					# want '/sub_f' but join(f, sub_f) would give just 'sub_f'.
					yield f + os.sep + sub_f
		def _normcase(self, path):
			return path if PLATFORM == 'Linux' else path.lower()

	def test_empty_suggests_recent_locations(self):
		expected_paths = [
			'~/Dropbox/Work', '~/Dropbox', '~/Downloads', '~/Dropbox/Private',
			'~/s-u-b-s-t-r', '~/My-substr', '~'
		]
		self._check_query_returns(
			'', expected_paths, [[]] * len(expected_paths)
		)
	def test_basename_matches(self):
		self._check_query_returns(
			'dow', ['~/Downloads', '~/Dropbox/Work'], [[2, 3, 4], [2, 4, 10]]
		)
	def test_exact_match_takes_precedence(self):
		expected_paths = [
			'~', '~/Dropbox', '~/Downloads', '~/s-u-b-s-t-r', '~/My-substr',
			'~/.hidden', '~/Unvisited'
		]
		self._check_query_returns(
			'~', expected_paths, [[0]] * len(expected_paths)
		)
	def test_prefix_match(self):
		self._check_query_returns('~/dow', ['~/Downloads'], [[0, 1, 2, 3, 4]])
	def test_existing_path(self):
		self._check_query_returns(
			'~/Unvisited', ['~/Unvisited', '~/Unvisited/Dir']
		)
	def test_subdirectories_of_paths_containing_parent_segments(self):
		self._check_query_returns(
			'~/Dropbox/../Do', ['~/Downloads'], [[0, 1, 2, 3]]
		)
	@skipIf(PLATFORM == 'Linux', 'Case-insensitive file systems only')
	def test_existing_path_wrong_case(self):
		self._check_query_returns(
			'~/unvisited', ['~/Unvisited', '~/Unvisited/Dir']
		)
	def test_enter_path_slash(self):
		highlight = list(range(len('~/Unvisited')))
		self._check_query_returns(
			'~/Unvisited/', ['~/Unvisited', '~/Unvisited/Dir'],
			[highlight, highlight]
		)
	def test_trailing_space(self):
		self._check_query_returns('~/Downloads ', [])
	def test_hidden(self):
		self._check_query_returns('~/.', ['~/.hidden'])
	def test_filesystem_search(self):
		# No visited paths:
		self.instance = SuggestLocations({}, self.fs)
		# Should still find Downloads by prefix:
		self._check_query_returns('dow', ['~/Downloads'], [[2, 3, 4]])
	def test_longer_query_skips_search_after_a_miss(self):
		instance = SuggestLocations({}, self.fs)
		for query in ['xyz', 'xyzq', 'xyzqw']:
			instance(query)
		self.assertEqual(['xyz'], self.fs.queried_prefixes)
	def test_miss_is_case_insensitive(self):
		instance = SuggestLocations({}, self.fs)
		instance('xyz')
		instance('XYZQ')
		self.assertEqual(['xyz'], self.fs.queried_prefixes)
	def test_search_continues_while_it_finds_folders(self):
		instance = SuggestLocations({}, self.fs)
		for query in ['dow', 'down', 'downl']:
			items = list(instance(query))
		self.assertEqual(
			['dow', 'down', 'downl'], self.fs.queried_prefixes
		)
		self.assertEqual(
			[os.path.join('~', 'Downloads')], [item.title for item in items]
		)
	def test_shorter_query_than_a_miss_searches_again(self):
		instance = SuggestLocations({}, self.fs)
		instance('dowx')
		items = list(instance('dow'))
		self.assertEqual(['dowx', 'dow'], self.fs.queried_prefixes)
		self.assertEqual(
			[os.path.join('~', 'Downloads')], [item.title for item in items]
		)
	def test_home_dir_expanded(self):
		self._check_query_returns(
			os.path.dirname(self.home_dir),
			[os.path.dirname(self.home_dir), self.home_dir]
		)
	def test_substring(self):
		# Should return My-substr before ~/s-u-b-s-t-r even though the latter
		# has a higher count:
		self._check_query_returns(
			'sub', ['~/My-substr', '~/s-u-b-s-t-r'], [[5, 6, 7], [2, 4, 6]]
		)
	def test_label_matches_when_the_path_does_not(self):
		# The home directory's title is '~', which contains none of h, o, m, e -
		# without its label, typing 'home' cannot find it.
		self.instance = SuggestLocations(
			self.instance.visited_paths, self.fs, labels={self.home_dir: 'Home'}
		)
		result = list(self.instance('home'))
		self.assertEqual(['~'], [item.title for item in result])
		# Nothing in the title to underline, as with a command-palette keyword
		# (QuicksearchItem turns highlight=None into []):
		self.assertEqual([[]], [item.highlight for item in result])
		self.assertEqual(['Home'], [item.hint for item in result])
	def test_label_is_shown_as_a_hint_even_when_the_path_matched(self):
		self.instance = SuggestLocations(
			self.instance.visited_paths, self.fs, labels={self.home_dir: 'Home'}
		)
		hints = {item.title: item.hint for item in self.instance('')}
		self.assertEqual('Home', hints['~'])
		self.assertEqual('', hints[self._replace_pathsep('~/Downloads')])
	def setUp(self):
		root = 'C:' if PLATFORM == 'Windows' else ''
		files = {
			root: {
				'Users': {
					'michael': {
						'.hidden': {},
						'Downloads': {},
						'Dropbox': {
							'Work': {}, 'Private': {}
						},
						'Unvisited': {
							'Dir': {}
						},
						'My-substr': {},
						's-u-b-s-t-r': {},
					}
				}
			},
			'.': {}
		}
		if PLATFORM == 'Windows':
			self.home_dir = r'C:\Users\michael'
		else:
			self.home_dir = '/Users/michael'
		self.fs = self.StubLocalFileSystem(files, home_dir=self.home_dir)
		visited_paths = {
			self._replace_pathsep(self.fs.expanduser(k)): v
			for k, v in [
				('~', 1),
				('~/Downloads', 5),
				('~/Dropbox', 6),
				('~/Dropbox/Work', 7),
				('~/Dropbox/Private', 4),
				('~/My-substr', 2),
				('~/s-u-b-s-t-r', 3) # Note: Higher count than My-substr
			]
		}
		self.instance = SuggestLocations(visited_paths, self.fs)
	def _check_query_returns(self, query, paths, highlights=None):
		query = self._replace_pathsep(query)
		paths = list(map(self._replace_pathsep, paths))
		if highlights is None:
			highlights = [self._full_range(query)] * len(paths)
		result = list(self.instance(query))
		self.assertEqual(paths, [item.title for item in result])
		self.assertEqual(highlights, [item.highlight for item in result])
	def _replace_pathsep(self, path):
		return path.replace('/', os.sep)
	def _full_range(self, string):
		return list(range(len(string)))
