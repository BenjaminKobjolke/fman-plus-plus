from core import selection_summary
from unittest import TestCase
from unittest.mock import patch


class _FileSystem:
	def __init__(self, entries, sizes=None, errors=None, aliases=None):
		self.entries = entries
		self.sizes = sizes or {}
		self.errors = errors or {}
		self.aliases = aliases or {}

	def is_dir(self, url):
		if url in self.errors:
			raise self.errors[url]
		return self.entries[url][0]

	def query(self, url, name):
		if url in self.errors:
			raise self.errors[url]
		return self.sizes.get(url)

	def iterdir(self, url):
		if url in self.errors:
			raise self.errors[url]
		return self.entries[url][1]

	def resolve(self, url):
		return self.aliases.get(url, url)


class SelectionSummaryTest(TestCase):
	def test_formats_singular_plural_and_omits_zero_counts(self):
		stats = selection_summary.SelectionStats(1, 2, 1024)
		self.assertEqual(
			'1 file, 2 folders selected, 1 KB',
			selection_summary.format_summary(stats),
		)
		self.assertEqual(
			'2 files selected',
			selection_summary.format_summary(
				selection_summary.SelectionStats(2, 0, None),
			),
		)
		self.assertEqual(
			'1 folder selected',
			selection_summary.format_summary(
				selection_summary.SelectionStats(0, 1, None),
			),
		)

	def test_formats_calculating_suffix(self):
		self.assertEqual(
			'1 folder selected, calculating...',
			selection_summary.format_summary(
				selection_summary.SelectionStats(0, 1, None, calculating=True),
			),
		)

	def test_measure_counts_selected_files_and_recursively_sums_folder_contents(self):
		fs = _FileSystem(
			{
				'file:///a.txt': (False, []),
				'file:///folder': (True, ['file:///folder/b.txt', 'file:///folder/sub']),
				'file:///folder/b.txt': (False, []),
				'file:///folder/sub': (True, ['file:///folder/sub/c.txt']),
				'file:///folder/sub/c.txt': (False, []),
			},
			{'file:///a.txt': 2, 'file:///folder/b.txt': 3,
			 'file:///folder/sub/c.txt': 5},
		)
		stats = selection_summary.measure(
			['file:///a.txt', 'file:///folder'], recursive=True, fs=fs,
		)
		self.assertEqual(selection_summary.SelectionStats(1, 1, 10), stats)

	def test_measure_does_not_walk_selected_folders_by_default(self):
		fs = _FileSystem({'file:///folder': (True, ['file:///folder/a.txt'])})
		stats = selection_summary.measure(
			['file:///folder'], fs=fs,
		)
		self.assertEqual(selection_summary.SelectionStats(0, 1, None), stats)

	def test_measure_skips_revisited_directories_and_honors_cancellation(self):
		fs = _FileSystem(
			{
				'file:///folder': (True, ['file:///folder/a.txt', 'file:///alias']),
				'file:///alias': (True, ['file:///folder/a.txt']),
				'file:///folder/a.txt': (False, []),
			},
			{'file:///folder/a.txt': 4},
			aliases={'file:///alias': 'file:///folder'},
		)
		checked = []
		stats = selection_summary.measure(
			['file:///folder'], recursive=True, fs=fs,
			is_cancelled=lambda: checked.append(True) or len(checked) > 2,
		)
		self.assertEqual(1, stats.folder_count)
		self.assertTrue(stats.calculating)
		self.assertGreaterEqual(len(checked), 3)

	def test_measure_skips_entries_that_raise_oserror(self):
		fs = _FileSystem(
			{
				'file:///folder': (True, ['file:///good.txt', 'file:///offline']),
				'file:///good.txt': (False, []),
			},
			{'file:///good.txt': 7},
			{'file:///offline': OSError('offline')},
		)
		stats = selection_summary.measure(
			['file:///folder'], recursive=True, fs=fs,
		)
		self.assertEqual(selection_summary.SelectionStats(0, 1, 7), stats)

	def test_default_filesystem_is_used_when_none_is_injected(self):
		with patch.object(selection_summary.default_fs, 'is_dir', return_value=False), \
				patch.object(selection_summary.default_fs, 'query', return_value=11):
			stats = selection_summary.measure(['file:///a.txt'])
		self.assertEqual(selection_summary.SelectionStats(1, 0, 11), stats)

	def test_location_setting_falls_back_to_pane_for_unknown_values(self):
		with patch.object(selection_summary, 'get_setting', return_value='unknown'):
			self.assertEqual(
				selection_summary.SelectionSummaryLocation.PANE,
				selection_summary.get_summary_location(),
			)

	def test_settings_use_the_approved_defaults_and_reject_invalid_boolean_values(self):
		with patch.object(selection_summary, 'get_setting', return_value='both'):
			self.assertEqual(
				selection_summary.SelectionSummaryLocation.BOTH,
				selection_summary.get_summary_location(),
			)
		with patch.object(selection_summary, 'get_setting', return_value=None):
			self.assertFalse(selection_summary.get_folder_sizes_enabled())
		with patch.object(selection_summary, 'get_setting', return_value=True):
			self.assertTrue(selection_summary.get_folder_sizes_enabled())

