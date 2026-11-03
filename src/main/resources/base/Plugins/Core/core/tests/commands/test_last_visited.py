from unittest import TestCase
from unittest.mock import patch

from core.commands import ClearLastVisitedHistory, ToggleRememberLastVisited
from core.commands.last_visited import (
	ClearLastVisitedHistory as ClearCommand,
	LastVisitedListener,
	ToggleRememberLastVisited as ToggleCommand,
	_history_key,
	_record_ancestors,
	_remember,
)
from core.tests.commands import FakePane


class LastVisitedHistoryTest(TestCase):
	def test_records_each_ancestor(self):
		history = {}

		_record_ancestors(history, 'file://C:/a/b/c')

		self.assertEqual({
			'file://C:/a/b': 'c',
			'file://C:/a': 'b',
			'file://C:': 'a',
		}, history)

	def test_updated_entry_moves_to_end_and_oldest_is_dropped(self):
		history = {'a': '1', 'b': '2', 'c': '3'}
		with patch('core.commands.last_visited.MAX_ENTRIES', 3):
			_remember(history, 'a', 'updated')
			_remember(history, 'd', '4')

		self.assertEqual({'c': '3', 'a': 'updated', 'd': '4'}, history)

	def test_history_key_removes_password_from_remote_authority(self):
		self.assertEqual(
			'ftp://user@host:21/x',
			_history_key('ftp://user:secret@host:21/x')
		)

	def test_history_key_preserves_file_and_password_free_urls(self):
		self.assertEqual('file://C:/x', _history_key('file://C:/x'))
		self.assertEqual('sftp://user@host/x', _history_key('sftp://user@host/x'))


class LastVisitedPane(FakePane):
	def __init__(self, path='file:///folder', cursor=None, home=None):
		super().__init__(url=cursor)
		self.path = path
		self.home = home
		self.placed = []

	def get_path(self):
		return self.path

	def _get_home_cursor(self):
		return self.home

	def place_cursor_at(self, url):
		self.placed.append(url)
		self._url = url


class LastVisitedListenerTest(TestCase):
	def setUp(self):
		self.history = {}
		self.pane = LastVisitedPane()
		self.listener = LastVisitedListener(self.pane)
		self.patches = (
			patch('core.commands.last_visited._history', return_value=self.history),
			patch('core.commands.last_visited.is_enabled', return_value=True),
			patch('core.commands.last_visited.is_incognito', return_value=False),
		)
		for item in self.patches:
			item.start()
			self.addCleanup(item.stop)

	def test_before_location_change_records_current_cursor_name(self):
		self.pane._url = 'file:///folder/child'

		self.listener.before_location_change('file:///folder', None)

		self.assertEqual({'file:///folder': 'child'}, self.history)

	def test_before_location_change_skips_incognito_disabled_and_empty_cursor(self):
		with patch('core.commands.last_visited.is_incognito', return_value=True):
			self.listener.before_location_change('file:///folder', None)
		self.assertEqual({}, self.history)
		with patch('core.commands.last_visited.is_enabled', return_value=False):
			self.listener.before_location_change('file:///folder', None)
		self.assertEqual({}, self.history)
		self.pane._url = None
		self.listener.before_location_change('file:///folder', None)
		self.assertEqual({}, self.history)

	def test_on_path_changed_reselects_when_cursor_is_on_home_row(self):
		self.pane._url = 'file:///folder/first'
		self.pane.home = self.pane._url
		self.history['file:///folder'] = 'remembered'

		self.listener.on_path_changed()

		self.assertEqual(['file:///folder/remembered'], self.pane.placed)

	def test_on_path_changed_does_not_override_explicit_or_moved_cursor(self):
		self.history['file:///folder'] = 'remembered'
		self.pane._url = 'file:///folder/first'
		self.pane.home = None
		self.listener.on_path_changed()
		self.pane.home = 'file:///folder/first'
		self.pane._url = 'file:///folder/moved'
		self.listener.on_path_changed()
		self.assertEqual([], self.pane.placed)

	def test_on_path_changed_drops_stale_entry(self):
		self.pane._url = 'file:///folder/first'
		self.pane.home = self.pane._url
		self.history['file:///folder'] = 'deleted'
		self.pane.place_cursor_at = lambda url: (_ for _ in ()).throw(ValueError())

		self.listener.on_path_changed()

		self.assertNotIn('file:///folder', self.history)

	def test_disabled_does_not_record_or_reselect(self):
		self.pane._url = 'file:///folder/first'
		self.pane.home = self.pane._url
		with patch('core.commands.last_visited.is_enabled', return_value=False):
			self.listener.on_path_changed()
		self.assertEqual({}, self.history)
		self.assertEqual([], self.pane.placed)

	def test_incognito_reselects_without_recording(self):
		self.pane.path = 'file:///folder/deep'
		self.pane._url = 'file:///folder/deep/first'
		self.pane.home = self.pane._url
		self.history['file:///folder/deep'] = 'remembered'
		with patch('core.commands.last_visited.is_incognito', return_value=True):
			self.listener.on_path_changed()
		self.assertEqual(['file:///folder/deep/remembered'], self.pane.placed)
		self.assertNotIn('file:///folder', self.history)


class LastVisitedCommandsTest(TestCase):
	def test_toggle_is_registered_and_reports_state(self):
		self.assertIs(ToggleRememberLastVisited, ToggleCommand)
		self.assertEqual(('Toggle remember last visited',), ToggleCommand.aliases)
		with (
			patch('core.commands.last_visited.is_enabled', side_effect=(True, False)),
			patch('core.commands.last_visited.save_setting') as save_setting,
			patch('core.commands.last_visited.show_status_message') as show_status,
		):
			command = ToggleCommand(None)
			command()
			command()
		save_setting.assert_has_calls([
			(('Core Settings.json', 'remember_last_visited', False),),
			(('Core Settings.json', 'remember_last_visited', True),),
		])
		show_status.assert_has_calls([
			(('Remember last visited: off',), {'timeout_secs': 3}),
			(('Remember last visited: on',), {'timeout_secs': 3}),
		])

	def test_clear_empties_cached_history_and_saves(self):
		self.assertIs(ClearLastVisitedHistory, ClearCommand)
		history = {'file:///folder': 'child'}
		with (
			patch('core.commands.last_visited._history', return_value=history),
			patch('core.commands.last_visited.save_json') as save_json,
			patch('core.commands.last_visited.show_status_message') as show_status,
		):
			ClearCommand(None)()
		self.assertEqual({}, history)
		save_json.assert_called_once_with('Last Visited.json')
		show_status.assert_called_once_with(
			'Last visited history cleared', timeout_secs=3)
