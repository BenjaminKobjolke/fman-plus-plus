from core.commands.file_mention import FileMention, suggest_mentions
from core.file_mention_index import IndexEntry
from core.tests.commands import FakePane
from fman import QuicksearchExit
from fman.url import as_url
from os.path import abspath, join
from unittest import TestCase
from unittest.mock import patch

_ROOT = abspath('proj')

def _entry(rel_path, is_dir=False):
	native = join(*rel_path.split('/'))
	return IndexEntry(join(_ROOT, native), native, is_dir)

class SuggestMentionsTest(TestCase):
	ENTRIES = [
		_entry('tools', is_dir=True), _entry('CLAUDE.md'),
		_entry('mod_loader.py'), _entry('tools/CLAUDE.md'),
		_entry('tickets/17057/plan.md'),
	]
	def test_name_prefix_ranks_above_substring_above_loose(self):
		titles = [i.title for i in suggest_mentions(self.ENTRIES, 'md')]
		self.assertEqual([
			'CLAUDE.md', 'tools/CLAUDE.md', 'tickets/17057/plan.md',
			'mod_loader.py'
		], titles)
	def test_every_word_must_appear_in_the_path(self):
		entries = [
			_entry('Rechnung_cip_ JFA_Reality_Webpage'),
			_entry('ryd/invoice.pdf'),
		]
		titles = [i.title for i in suggest_mentions(entries, '@pdf ryd')]
		self.assertEqual(['ryd/invoice.pdf'], titles)
	def test_several_words_find_no_scattered_letters(self):
		entries = [
			_entry('2026_10_05_Streifen.sync-conflict-20261104-ESYBYDW.pdf'),
			_entry('ryd/2026_11_16_invoice.pdf'),
		]
		titles = [
			i.title for i in suggest_mentions(entries, '@ryd pdf 2026 11 16')
		]
		self.assertEqual(['ryd/2026_11_16_invoice.pdf'], titles)
	def test_name_prefix_comes_first(self):
		titles = [i.title for i in suggest_mentions(self.ENTRIES, 'plan')]
		self.assertEqual(['tickets/17057/plan.md'], titles)
	def test_mention_prefix_is_ignored(self):
		self.assertEqual(
			[i.title for i in suggest_mentions(self.ENTRIES, 'md')],
			[i.title for i in suggest_mentions(self.ENTRIES, '@md')]
		)
	def test_folders_end_in_a_slash_and_rows_hold_absolute_paths(self):
		item, = suggest_mentions(self.ENTRIES, 'tool')[:1]
		self.assertEqual('tools/', item.title)
		self.assertEqual(join(_ROOT, 'tools'), item.value.path)
	def test_empty_query_keeps_index_order(self):
		titles = [i.title for i in suggest_mentions(self.ENTRIES, '@')]
		self.assertEqual('tools/', titles[0])
		self.assertEqual(len(self.ENTRIES), len(titles))
	def test_rows_are_capped(self):
		entries = [_entry('f%d.md' % i) for i in range(10)]
		with patch('core.commands.file_mention.RESULT_LIMIT', 3):
			self.assertEqual(3, len(suggest_mentions(entries, 'md')))

class _Pane(FakePane):
	def __init__(self, url):
		super().__init__(url=url)
		self.set_path_calls = []
		self.cursor = None
	def get_path(self):
		return self._url
	def set_path(self, url, callback=None):
		self.set_path_calls.append(url)
		if callback:
			callback()
	def place_cursor_at(self, url):
		self.cursor = url

class _StubIndex:
	def __init__(self, root, excluded):
		self.root, self.excluded = root, excluded
		self.started = self.stopped = False
	def start(self):
		self.started = True
	def stop(self):
		self.stopped = True
	def set_refresh(self, fn):
		pass
	def snapshot(self):
		return []

class FileMentionCommandTest(TestCase):
	def test_enter_on_a_folder_opens_it(self):
		pane, index = self._run(join(_ROOT, 'tools'), is_dir=True)
		self.assertEqual([as_url(join(_ROOT, 'tools'))], pane.set_path_calls)
		self.assertTrue(index.started and index.stopped)
	def test_enter_on_a_file_places_the_cursor_on_it(self):
		path = join(_ROOT, 'tools', 'CLAUDE.md')
		pane, _ = self._run(path, is_dir=False)
		self.assertEqual([as_url(join(_ROOT, 'tools'))], pane.set_path_calls)
		self.assertEqual(as_url(path), pane.cursor)
	def test_switch_runs_the_other_popup(self):
		result = QuicksearchExit('md', 'go_to', from_text=True)
		pane, index = self._run(result=result)
		self.assertEqual(['go_to'], pane.commands_run)
		self.assertTrue(index.stopped)
	def test_non_local_folder_shows_a_message(self):
		pane = _Pane('zip://C:/a.zip')
		with patch('core.commands.file_mention.show_quicksearch') as show, \
				patch('core.commands.file_mention.show_status_message') as msg:
			FileMention(pane)()
		show.assert_not_called()
		msg.assert_called_once()
	def test_switch_query_does_not_double_the_prefix(self):
		pane = _Pane(as_url(_ROOT))
		with patch('core.commands.file_mention.FileMentionIndex', _StubIndex), \
				patch(
					'core.commands.file_mention.show_quicksearch',
					return_value=None
				) as show:
			FileMention(pane)(query='@md', continue_typing=True)
		self.assertEqual('@md', show.call_args.kwargs['query'])
		self.assertEqual(3, show.call_args.kwargs['select_from'])
	def _run(self, path=None, is_dir=False, result=None):
		pane = _Pane(as_url(_ROOT))
		indexes = []
		def make_index(root, excluded):
			indexes.append(_StubIndex(root, excluded))
			return indexes[-1]
		if result is None:
			result = ('@x', IndexEntry(path, 'x', is_dir))
		with patch('core.commands.file_mention.FileMentionIndex', make_index), \
				patch(
					'core.commands.file_mention.show_quicksearch',
					return_value=result
				):
			FileMention(pane)()
		return pane, indexes[0]
