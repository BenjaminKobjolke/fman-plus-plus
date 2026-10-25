from core.commands.hidden_files import _get_pane_info, _hidden_file_filter, \
	_forget_pane_info, _is_hidden_file, _toggle_hidden_files
from fman import PLATFORM
from stat import FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_NORMAL
from unittest import TestCase, skipIf
from unittest.mock import MagicMock, patch

@skipIf(PLATFORM != 'Windows', 'Skip Windows-only test')
class HiddenFileFilterTest(TestCase):

	"""
	The filter runs in the GUI thread (Model#_record_files_main/#update), so it
	must not perform an FS round trip of its own - see #_stat(...).
	"""

	_URL = 'file://C:/dir/file.txt'

	def test_hidden(self):
		self.assertFalse(self._filter(stat=_StubStat(FILE_ATTRIBUTE_HIDDEN)))
	def test_not_hidden(self):
		self.assertTrue(self._filter(stat=_StubStat(FILE_ATTRIBUTE_NORMAL)))
	def test_stat_fails(self):
		self.assertTrue(self._filter(error=OSError()))
	def test_other_scheme_is_not_stated(self):
		with patch('core.commands.hidden_files.query') as query:
			self.assertTrue(_hidden_file_filter('zip://C:/a.zip/file.txt'))
		query.assert_not_called()
	def _filter(self, stat=None, error=None, url=_URL):
		with patch(
			'core.commands.hidden_files.query',
			return_value=stat, side_effect=error
		):
			return _hidden_file_filter(url)

class _StubStat:
	def __init__(self, st_file_attributes):
		self.st_file_attributes = st_file_attributes

class GetPaneInfoTest(TestCase):

	"""
	'Panes.json' is a list indexed by pane position, so it has to be padded up
	to that index before it can be read. Each pane must get its *own* dict: a
	shared one would make toggling hidden files in one pane silently toggle it
	in the other.
	"""

	def test_existing_pane(self):
		settings = [{'show_hidden_files': True}]
		self.assertEqual(
			{'show_hidden_files': True}, self._info(0, settings)
		)
	def test_pads_up_to_the_pane_index(self):
		settings = []
		self.assertEqual(
			{'show_hidden_files': False}, self._info(1, settings, num_panes=2)
		)
		self.assertEqual(2, len(settings))
	def test_each_padded_pane_gets_its_own_dict(self):
		settings = []
		self._info(0, settings, num_panes=2)['show_hidden_files'] = True
		self.assertEqual(
			{'show_hidden_files': False}, self._info(1, settings, num_panes=2)
		)
	def _info(self, pane_index, settings, num_panes=1):
		panes = [MagicMock() for _ in range(num_panes)]
		pane = panes[pane_index]
		pane.window.get_panes.return_value = panes
		with patch(
			'core.commands.hidden_files.load_json', return_value=settings
		):
			return _get_pane_info(pane)

class ToggleHiddenFilesTest(TestCase):

	"""
	Showing hidden files *removes* the filter; hiding them adds it. The write
	to 'Panes.json' has to be flushed immediately - see #_toggle_hidden_files.
	"""

	def test_showing_removes_the_filter(self):
		pane, settings, save_json = self._toggle(True)
		pane._remove_filter.assert_called_once_with(_hidden_file_filter)
		pane._set_dimmer.assert_called_once_with(_is_hidden_file)
		pane._add_filter.assert_not_called()
		self.assertTrue(settings[0]['show_hidden_files'])
		save_json.assert_called_once_with('Panes.json')
	def test_hiding_adds_the_filter(self):
		pane, settings, _ = self._toggle(False)
		pane._add_filter.assert_called_once_with(_hidden_file_filter)
		pane._set_dimmer.assert_called_once_with(None)
		pane._remove_filter.assert_not_called()
		self.assertFalse(settings[0]['show_hidden_files'])
	def _toggle(self, value):
		pane = MagicMock()
		pane.window.get_panes.return_value = [pane]
		settings = []
		with patch(
			'core.commands.hidden_files.load_json', return_value=settings
		), patch('core.commands.hidden_files.save_json') as save_json, patch(
			'core.commands.hidden_files.get_setting', return_value=True
		):
			_toggle_hidden_files(pane, value)
		return pane, settings, save_json
	def test_setting_disables_dimming(self):
		pane = MagicMock()
		pane.window.get_panes.return_value = [pane]
		with patch(
			'core.commands.hidden_files.load_json', return_value=[]
		), patch('core.commands.hidden_files.save_json'), patch(
			'core.commands.hidden_files.get_setting', return_value=False
		):
			_toggle_hidden_files(pane, True)
		pane._set_dimmer.assert_called_once_with(None)
	def test_non_file_locations_are_not_dimmed(self):
		self.assertFalse(_is_hidden_file('zip://C:/archive.zip/file.txt'))

class ForgetPaneInfoTest(TestCase):
	def test_deletes_entry_and_saves(self):
		panes = [MagicMock(), MagicMock(), MagicMock()]
		panes[1].window.get_panes.return_value = panes
		settings = [{'i': 0}, {'i': 1}, {'i': 2}]
		with patch('core.commands.hidden_files.load_json', return_value=settings), \
				patch('core.commands.hidden_files.save_json') as save_json:
			_forget_pane_info(panes[1])
		self.assertEqual([{'i': 0}, {'i': 2}], settings)
		save_json.assert_called_once_with('Panes.json')
	def test_out_of_range_does_not_change_or_save(self):
		pane = MagicMock()
		pane.window.get_panes.return_value = [MagicMock(), pane]
		settings = [{'i': 0}]
		with patch('core.commands.hidden_files.load_json', return_value=settings), \
				patch('core.commands.hidden_files.save_json') as save_json:
			_forget_pane_info(pane)
		self.assertEqual([{'i': 0}], settings)
		save_json.assert_not_called()
