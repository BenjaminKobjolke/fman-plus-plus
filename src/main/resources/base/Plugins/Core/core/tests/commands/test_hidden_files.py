from core.commands.hidden_files import _get_pane_info, _hidden_file_filter, \
	_forget_pane_info, _is_hidden_file, _toggle_hidden_files
from fman import PLATFORM
from stat import FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_NORMAL, FILE_ATTRIBUTE_READONLY
from unittest import TestCase, skipIf
from unittest.mock import MagicMock, patch

import os
import tempfile

if PLATFORM == 'Windows':
	from core.commands.hidden_files import _apply_hidden_attribute, \
		_set_hidden_attribute, SetHiddenAttribute

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

@skipIf(PLATFORM != 'Windows', 'Skip Windows-only test')
class HiddenAttributeTest(TestCase):
	def test_sets_and_clears_hidden_attribute(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, 'file.txt')
			with open(path, 'w'):
				pass
			_set_hidden_attribute(path, True)
			self.assertTrue(os.stat(path).st_file_attributes & FILE_ATTRIBUTE_HIDDEN)
			_set_hidden_attribute(path, False)
			self.assertFalse(os.stat(path).st_file_attributes & FILE_ATTRIBUTE_HIDDEN)

	def test_clearing_hidden_keeps_other_attributes(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, 'file.txt')
			with open(path, 'w'):
				pass
			os.chmod(path, FILE_ATTRIBUTE_READONLY)
			_set_hidden_attribute(path, True)
			try:
				_set_hidden_attribute(path, False)
				attrs = os.stat(path).st_file_attributes
				self.assertTrue(attrs & FILE_ATTRIBUTE_READONLY)
				self.assertFalse(attrs & FILE_ATTRIBUTE_HIDDEN)
			finally:
				os.chmod(path, FILE_ATTRIBUTE_NORMAL)

	def test_clearing_only_attribute_succeeds(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, 'file.txt')
			with open(path, 'w'):
				pass
			os.chmod(path, FILE_ATTRIBUTE_NORMAL)
			_set_hidden_attribute(path, True)
			_set_hidden_attribute(path, False)
			self.assertFalse(os.stat(path).st_file_attributes & FILE_ATTRIBUTE_HIDDEN)

	def test_works_on_directory(self):
		with tempfile.TemporaryDirectory() as directory:
			_set_hidden_attribute(directory, True)
			self.assertTrue(
				os.stat(directory).st_file_attributes & FILE_ATTRIBUTE_HIDDEN
			)
			_set_hidden_attribute(directory, False)
			self.assertFalse(
				os.stat(directory).st_file_attributes & FILE_ATTRIBUTE_HIDDEN
			)

	def test_missing_path_raises_os_error(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, 'missing')
			with self.assertRaises(OSError):
				_set_hidden_attribute(path, True)

@skipIf(PLATFORM != 'Windows', 'Skip Windows-only test')
class ApplyHiddenAttributeTest(TestCase):
	def setUp(self):
		self.command = MagicMock(spec=SetHiddenAttribute(MagicMock()))
		self.command.pane = MagicMock()
		self.command.pane.get_path.return_value = 'file:///dir'

	def test_applies_to_each_file_and_refreshes_directory(self):
		files = ['file:///dir/one', 'file:///dir/two']
		with patch('core.commands.hidden_files.chosen_files', return_value=files), \
				patch(
					'core.commands.hidden_files.as_human_readable',
					side_effect=lambda url: url
				), \
				patch(
					'core.commands.hidden_files._set_hidden_attribute'
				) as set_attribute, \
				patch('core.commands.hidden_files.notify_file_changed') as notify, \
				patch('core.commands.hidden_files.show_status_message') as status, \
				patch('core.commands.hidden_files.show_alert') as alert:
			_apply_hidden_attribute(self.command, True)
		self.assertEqual([
			((files[0], True),), ((files[1], True),)
		], set_attribute.call_args_list)
		notify.assert_called_once_with('file:///dir')
		status.assert_called_once_with(
			'Hidden attribute set on 2 files', timeout_secs=3
		)
		alert.assert_not_called()

	def test_skips_non_file_url_and_reports_it(self):
		files = ['zip://archive/file', 'file:///dir/file']
		with patch('core.commands.hidden_files.chosen_files', return_value=files), \
				patch(
					'core.commands.hidden_files.as_human_readable',
					side_effect=lambda url: url
				), \
				patch(
					'core.commands.hidden_files._set_hidden_attribute'
				) as set_attribute, \
				patch('core.commands.hidden_files.notify_file_changed') as notify, \
				patch('core.commands.hidden_files.show_alert') as alert, \
				patch('core.commands.hidden_files.show_status_message') as status:
			_apply_hidden_attribute(self.command, False)
		set_attribute.assert_called_once_with(files[1], False)
		notify.assert_called_once_with('file:///dir')
		alert.assert_called_once()
		self.assertIn(files[0], alert.call_args[0][0])
		status.assert_not_called()

	def test_os_error_does_not_stop_remaining_files_and_refreshes(self):
		files = ['file:///dir/first', 'file:///dir/second']
		with patch('core.commands.hidden_files.chosen_files', return_value=files), \
				patch(
					'core.commands.hidden_files.as_human_readable',
					side_effect=lambda url: url
				), \
				patch(
					'core.commands.hidden_files._set_hidden_attribute',
					side_effect=[OSError('denied'), None]
				) as set_attribute, \
				patch('core.commands.hidden_files.notify_file_changed') as notify, \
				patch('core.commands.hidden_files.show_alert') as alert:
			_apply_hidden_attribute(self.command, True)
		self.assertEqual(2, set_attribute.call_count)
		notify.assert_called_once_with('file:///dir')
		alert.assert_called_once()
		self.assertIn(files[0], alert.call_args[0][0])

	def test_no_chosen_files_does_nothing(self):
		with patch('core.commands.hidden_files.chosen_files', return_value=[]), \
				patch(
					'core.commands.hidden_files._set_hidden_attribute'
				) as set_attribute, \
				patch('core.commands.hidden_files.notify_file_changed') as notify:
			_apply_hidden_attribute(self.command, True)
		set_attribute.assert_not_called()
		notify.assert_not_called()
