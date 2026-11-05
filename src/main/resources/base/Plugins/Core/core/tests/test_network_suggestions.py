from unittest import TestCase
from unittest.mock import Mock

from core.network_suggestions import (
	NetworkLookups, NetworkSuggestion, NetworkSuggestions,
)
from core.fs.local.windows.shares import ShareConnection
from core.suggest_locations import SuggestLocations
from fman import QuicksearchItem


class NetworkSuggestionsTest(TestCase):
	class ThreadStarter:
		def __init__(self):
			self.targets = []

		def __call__(self, target):
			self.targets.append(target)

		def run(self, index=0):
			self.targets[index]()

	class Clock:
		def __init__(self):
			self.now = 0

		def __call__(self):
			return self.now

	def _lookups(self, list_servers=None, list_shares=None):
		self.threads = self.ThreadStarter()
		self.clock = self.Clock()
		return NetworkLookups(
			list_servers or (lambda: []),
			list_shares or (lambda _server: []),
			self.clock,
			self.threads,
		)

	def _suggestions(self, lookups, visited=(), connections=()):
		return NetworkSuggestions(
			{path: index for index, path in enumerate(visited)},
			lookups,
			lambda: connections,
		)

	def test_pending_host_scan_shows_known_hosts_and_starts_once(self):
		lookups = self._lookups(lambda: ['ServerTwo', 'serverone'])
		suggestions = self._suggestions(
			lookups,
			[r'\\ServerOne\Share', r'\\serverone\Other'],
			[ShareConnection('', r'\\SERVERONE\Connected'),
				 ShareConnection('', r'\\ServerThree\Share')],
		)

		for query in (r'\\', r'\\se'):
			result = suggestions(query)
			self.assertEqual(
				{r'\\ServerOne', r'\\ServerThree'}, set(result.dirs)
			)
			self.assertEqual('Searching network…', result.status.hint)
		self.assertEqual(1, len(self.threads.targets))

	def test_host_scan_refreshes_once_and_cached_hosts_replace_status(self):
		lookups = self._lookups(lambda: ['ServerOne', 'ServerTwo'])
		suggestions = self._suggestions(lookups, [r'\\Known\Share'])
		refresh = Mock(spec=lambda: None)
		suggestions.set_refresh(refresh)
		other_suggestions = self._suggestions(lookups)
		other_refresh = Mock(spec=lambda: None)
		other_suggestions.set_refresh(other_refresh)

		suggestions(r'\\')
		other_suggestions(r'\\')
		self.threads.run()
		result = suggestions(r'\\')

		self.assertEqual(
			{r'\\Known', r'\\ServerOne', r'\\ServerTwo'}, set(result.dirs)
		)
		self.assertIsNone(result.status)
		refresh.assert_called_once_with()
		other_refresh.assert_called_once_with()
		self.assertEqual(1, len(self.threads.targets))

	def test_share_lookup_shows_known_and_scanned_shares(self):
		lookups = self._lookups(
			list_shares=lambda server: self.assertEqual('HOST', server) or ['ShareOne']
		)
		suggestions = self._suggestions(
			lookups,
			[r'\\HOST\Visited'],
			[ShareConnection('', r'\\host\Connected')],
		)
		refresh = Mock(spec=lambda: None)
		suggestions.set_refresh(refresh)

		pending = suggestions('\\\\HOST\\')
		self.assertEqual('Searching network…', pending.status.hint)
		self.assertEqual(1, len(self.threads.targets))
		self.threads.run()
		result = suggestions(r'\\HOST\sh')

		self.assertEqual(
			{r'\\HOST\Visited', r'\\HOST\Connected', r'\\HOST\ShareOne'},
			set(result.dirs),
		)
		self.assertIsNone(result.status)
		refresh.assert_called_once_with()

	def test_failed_share_lookup_shows_no_answer_and_retries_after_30_seconds(self):
		def fail(_server):
			raise FileNotFoundError()

		lookups = self._lookups(list_shares=fail)
		suggestions = self._suggestions(lookups)

		self.assertEqual('Searching network…', suggestions('\\\\HOST\\').status.hint)
		self.threads.run()
		self.assertEqual('Did not answer', suggestions('\\\\HOST\\').status.hint)
		self.assertEqual(1, len(self.threads.targets))
		self.clock.now = 29
		self.assertEqual('Did not answer', suggestions('\\\\HOST\\').status.hint)
		self.assertEqual(1, len(self.threads.targets))
		self.clock.now = 30
		self.assertEqual('Searching network…', suggestions('\\\\HOST\\').status.hint)
		self.assertEqual(2, len(self.threads.targets))

	def test_empty_share_list_shows_no_shared_folders(self):
		lookups = self._lookups(list_shares=lambda _server: [])
		suggestions = self._suggestions(lookups)

		suggestions('\\\\HOST\\')
		self.threads.run()

		self.assertEqual(
			'No shared folders', suggestions('\\\\HOST\\').status.hint
		)

	def test_successful_share_cache_expires_after_300_seconds(self):
		calls = []
		lookups = self._lookups(
			list_shares=lambda server: calls.append(server) or ['Share']
		)
		suggestions = self._suggestions(lookups)

		suggestions('\\\\HOST\\')
		self.threads.run()
		suggestions('\\\\HOST\\')
		self.assertEqual(1, len(calls))
		self.clock.now = 299
		suggestions('\\\\HOST\\')
		self.assertEqual(1, len(calls))
		self.clock.now = 300
		suggestions('\\\\HOST\\')
		self.assertEqual(2, len(self.threads.targets))
		self.threads.run(1)
		self.assertEqual(2, len(calls))

	def test_non_network_and_deeper_paths_are_not_handled(self):
		suggestions = self._suggestions(self._lookups())
		for query in (
			'C:\\x', r'\\HOST\share\sub', 'smb://server/share',
		):
			with self.subTest(query=query):
				self.assertIsNone(suggestions(query))
		self.assertEqual([], self.threads.targets)

	def test_suggest_locations_uses_network_dirs_and_status_without_filesystem_io(self):
		status = QuicksearchItem(None, r'\\', hint='Searching network…')
		network = Mock(spec=NetworkSuggestions, return_value=NetworkSuggestion(
			[r'\\server-one', r'\\server-two'], status
		))
		fs = Mock(spec=SuggestLocations.LocalFileSystem)
		fs.expanduser.side_effect = lambda path: path
		suggestions = SuggestLocations({}, fs, network=network)

		items = suggestions(r'\\se')

		self.assertEqual(
			[r'\\server-one', r'\\server-two', None],
			[item.value for item in items]
		)
		self.assertEqual('Searching network…', items[-1].hint)
		network.assert_called_once_with(r'\\se')
		fs.isdir.assert_not_called()
		fs.listdir.assert_not_called()

	def test_suggest_locations_falls_back_when_network_does_not_handle_query(self):
		network = Mock(spec=NetworkSuggestions, return_value=None)
		fs = Mock(spec=SuggestLocations.LocalFileSystem)
		fs.expanduser.side_effect = lambda path: path
		fs.find_folders_starting_with.return_value = ['existing-folder']
		suggestions = SuggestLocations({}, fs, network=network)

		suggestions('fol')

		network.assert_called_once_with('fol')
		fs.find_folders_starting_with.assert_called_once_with('fol')
