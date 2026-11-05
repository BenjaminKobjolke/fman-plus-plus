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
