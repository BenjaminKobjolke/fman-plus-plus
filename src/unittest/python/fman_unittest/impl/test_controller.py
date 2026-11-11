from fman import DirectoryPane
from fman.impl.controller import Controller
from threading import Event
from unittest import TestCase
from unittest.mock import MagicMock


class ControllerEditNameTest(TestCase):

	_URL = 'file://C:/dir/a.txt'

	def setUp(self):
		self._error_handler = _StubErrorHandler()
		self._controller = Controller(
			MagicMock(), MagicMock(), MagicMock(), MagicMock(),
			self._error_handler
		)
		self._pane_widget = MagicMock()
		self._pane = DirectoryPane(
			window=MagicMock(), widget=MagicMock(),
			command_registry=MagicMock()
		)
		self._controller.register_pane(self._pane_widget, self._pane)
		self._listener = _RecordingListener()
		self._pane._add_listener(self._listener)

	def test_edit_name_callback_replaces_listener_broadcast(self):
		called = Event()
		callback_args = []

		def callback(*args):
			callback_args.append(args)
			called.set()

		self._pane.edit_name(self._URL, callback=callback)
		self._controller.on_file_renamed(
			self._pane_widget, self._URL, 'new'
		)

		self.assertTrue(called.wait(5))
		self.assertEqual([(self._URL, 'new')], callback_args)
		self.assertEqual([], self._listener.calls)

	def test_edit_name_without_callback_broadcasts_legacy_event(self):
		self._pane.edit_name(self._URL)

		self._controller.on_file_renamed(
			self._pane_widget, self._URL, 'new'
		)

		self.assertEqual([(self._URL, 'new')], self._listener.calls)

	def test_latest_edit_name_call_replaces_callback(self):
		called = Event()
		callback = MagicMock(side_effect=lambda *args: called.set())
		self._pane.edit_name(self._URL, callback=callback)
		self._pane.edit_name(self._URL)

		self._controller.on_file_renamed(
			self._pane_widget, self._URL, 'new'
		)

		self.assertEqual([(self._URL, 'new')], self._listener.calls)
		callback.assert_not_called()

	def test_edit_name_callback_is_consumed_after_commit(self):
		called = Event()
		callback = MagicMock(side_effect=lambda *args: called.set())
		self._pane.edit_name(self._URL, callback=callback)

		self._controller.on_file_renamed(
			self._pane_widget, self._URL, 'new'
		)
		self.assertTrue(called.wait(5))
		self._controller.on_file_renamed(
			self._pane_widget, self._URL, 'newer'
		)

		callback.assert_called_once_with(self._URL, 'new')
		self.assertEqual([(self._URL, 'newer')], self._listener.calls)

	def test_callback_error_is_reported(self):
		called = Event()

		def callback(*args):
			called.set()
			raise ValueError('bad callback')

		self._pane.edit_name(self._URL, callback=callback)
		self._controller.on_file_renamed(
			self._pane_widget, self._URL, 'new'
		)

		self.assertTrue(called.wait(5))
		self.assertTrue(self._error_handler.reported.wait(5))
		self.assertEqual(1, len(self._error_handler.calls))
		message, error = self._error_handler.calls[0]
		self.assertIn('callback', message)
		self.assertIsInstance(error, ValueError)

	def test_edit_name_passes_selection_to_widget(self):
		callback = MagicMock()

		self._pane.edit_name(self._URL, 1, 3, callback=callback)

		self._pane._widget.edit_name.assert_called_once_with(self._URL, 1, 3)


class ControllerZoomTest(TestCase):

	def setUp(self):
		self.controller = Controller(
			MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
		)
		self.pane_widget = MagicMock()
		self.pane = MagicMock()
		self.controller._panes[self.pane_widget] = self.pane

	def test_positive_step_runs_increase_command(self):
		self.pane.get_commands.return_value = {'increase_pane_font_size'}

		self.controller.on_zoom_step(self.pane_widget, 1)

		self.pane.run_command.assert_called_once_with(
			'increase_pane_font_size'
		)

	def test_negative_step_runs_decrease_command(self):
		self.pane.get_commands.return_value = {'decrease_pane_font_size'}

		self.controller.on_zoom_step(self.pane_widget, -1)

		self.pane.run_command.assert_called_once_with(
			'decrease_pane_font_size'
		)

	def test_missing_zoom_command_is_ignored(self):
		self.pane.get_commands.return_value = set()

		self.controller.on_zoom_step(self.pane_widget, 1)

		self.pane.run_command.assert_not_called()


class _RecordingListener:
	def __init__(self):
		self.calls = []
	def on_name_edited(self, *args):
		self.calls.append(args)


class _StubErrorHandler:
	def __init__(self):
		self.calls = []
		self.reported = Event()
	def report(self, message, exc):
		self.calls.append((message, exc))
		self.reported.set()


class ControllerLocationBarTest(TestCase):
	def setUp(self):
		self.metrics = MagicMock()
		self.usage_helper = MagicMock()
		self.controller = Controller(
			MagicMock(), MagicMock(), self.usage_helper, self.metrics,
			MagicMock()
		)
		self.pane_widget = MagicMock()
		self.pane = MagicMock(spec=DirectoryPane)
		self.controller._panes[self.pane_widget] = self.pane

	def test_navigation_places_cursor_on_child_and_switches_scheme(self):
		self.pane.get_path.side_effect = [
			'zip://C:/archive.zip/folder/current',
			'file://C:/archive.zip'
		]

		self.controller.on_location_bar_segment_clicked(
			self.pane_widget, 'zip://C:/archive.zip'
		)

		self.pane.set_path.assert_called_once()
		path, callback = self.pane.set_path.call_args.args
		self.assertEqual('zip://C:/archive.zip', path)
		callback()
		self.pane.place_cursor_at.assert_called_once_with(
			'file://C:/archive.zip/folder'
		)
		self.pane.move_cursor_home.assert_not_called()
		self.metrics.track.assert_not_called()
		self.usage_helper.on_location_bar_clicked.assert_not_called()

	def test_navigation_swallows_missing_parent(self):
		self.pane.get_path.return_value = 'file:///home/user/project'
		self.pane.set_path.side_effect = FileNotFoundError

		self.controller.on_location_bar_segment_clicked(
			self.pane_widget, 'file:///home/user'
		)

		self.pane.set_path.assert_called_once()

	def test_missing_cursor_target_falls_back_to_home(self):
		self.pane.get_path.side_effect = [
			'file:///home/user/project',
			'file:///home/user'
		]
		self.pane.place_cursor_at.side_effect = ValueError

		self.controller.on_location_bar_segment_clicked(
			self.pane_widget, 'file:///home'
		)

		_, callback = self.pane.set_path.call_args.args
		callback()
		self.pane.move_cursor_home.assert_called_once_with()
