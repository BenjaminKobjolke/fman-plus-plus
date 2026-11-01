from fman.impl.session import SessionManager
from fman.impl.single_instance import (
	SingleInstance, bring_to_front, open_paths_in_running_instance,
	panes_active_first
)
from os import getpid
from PyQt5.QtCore import QEventLoop, Qt
from PyQt5.QtNetwork import QLocalSocket
from PyQt5.QtWidgets import QApplication
from unittest import TestCase

class SingleInstanceTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls._app = QApplication.instance() or QApplication([])
	def setUp(self):
		self._server_name = 'fman-test-si-%s-%s' % (getpid(), id(self))
		self._primary = None
	def tearDown(self):
		if self._primary is not None and self._primary._server is not None:
			self._primary._server.close()
	def test_forward_delivers_paths_to_primary(self):
		received = []
		self._primary = SingleInstance(
			self._server_name,
			lambda paths, single_pane: received.append((paths, single_pane))
		)
		self._primary.start_listening()
		client = SingleInstance(self._server_name, lambda paths, single_pane: None)
		self.assertTrue(client.try_forward(['C:/x', 'C:/y'], single_pane=True))
		# processEvents with a wait gives the OS time to deliver newConnection:
		for _ in range(300):
			if received:
				break
			self._app.processEvents(QEventLoop.AllEvents, 10)
		self.assertEqual([(['C:/x', 'C:/y'], True)], received)
	def test_old_list_payload_delivers_paths_without_single_pane(self):
		received = []
		self._primary = SingleInstance(
			self._server_name,
			lambda paths, single_pane: received.append((paths, single_pane))
		)
		self._primary.start_listening()
		socket = QLocalSocket()
		socket.connectToServer(self._server_name)
		self.assertTrue(socket.waitForConnected(3000))
		socket.write(b'["C:/legacy"]')
		socket.flush()
		socket.waitForBytesWritten(3000)
		socket.disconnectFromServer()
		for _ in range(300):
			if received:
				break
			self._app.processEvents(QEventLoop.AllEvents, 10)
		self.assertEqual([(['C:/legacy'], False)], received)
	def test_forward_returns_false_when_no_primary(self):
		client = SingleInstance(self._server_name, lambda paths, single_pane: None)
		self.assertFalse(client.try_forward(['C:/x']))

class OpenPathsInRunningInstanceTest(TestCase):
	def test_single_pane_runs_command_on_active_pane(self):
		left, right = _FakePane(), _FakePane()
		plugin_support = _FakePluginSupport([left, right], active=right)
		session = _RecordingSessionManager()

		open_paths_in_running_instance(
			_WindowState(0), plugin_support, session, ['C:/x'], single_pane=True
		)

		self.assertEqual([('show_only_active_pane',)], right.commands)
		self.assertEqual([('C:/x', right)], session.opened)
	def test_single_pane_runs_command_without_paths(self):
		pane = _FakePane()
		plugin_support = _FakePluginSupport([pane], active=pane)

		open_paths_in_running_instance(
			_WindowState(0), plugin_support, _RecordingSessionManager(), [],
			single_pane=True
		)

		self.assertEqual([('show_only_active_pane',)], pane.commands)

class OpenPathInPaneTest(TestCase):
	def _create_session_manager(self, fs):
		return SessionManager({}, fs, _RecordingErrorHandler(), '0')
	def test_open_directory_sets_that_location(self):
		fs = _FakeFs(dirs=['file://C:/a'])
		pane = _FakePane()
		self._create_session_manager(fs).open_path_in_pane(pane, 'file://C:/a')
		self.assertEqual('file://C:/a', pane.location)
		self.assertIsNone(pane.callback)
		self.assertIsNone(pane.cursor_url)
	def test_open_file_sets_parent_and_places_cursor(self):
		fs = _FakeFs(dirs=['file://C:/a'], files=['file://C:/a/b'])
		pane = _FakePane()
		self._create_session_manager(fs).open_path_in_pane(pane, 'file://C:/a/b')
		self.assertEqual('file://C:/a', pane.location)
		self.assertIsNotNone(pane.callback)
		# The recorded callback places the cursor on the file:
		pane.callback()
		self.assertEqual('file://C:/a/b', pane.cursor_url)

class PanesActiveFirstTest(TestCase):
	def test_uses_get_active_pane_when_available(self):
		left, right = _FakePane(), _FakePane()
		plugin_support = _FakePluginSupport([left, right], active=right)
		panes = panes_active_first(plugin_support, _FakeMainWindow(None))
		self.assertEqual([right, left], panes)
	def test_falls_back_to_focus_widget_when_no_active_pane(self):
		# Window in the background: no pane has live focus, but focusWidget()
		# still points into the right pane's widget subtree.
		left, right = _FakePane(), _FakePane()
		main_window = _FakeMainWindow(right.child_widget)
		plugin_support = _FakePluginSupport([left, right], active=None)
		panes = panes_active_first(plugin_support, main_window)
		self.assertEqual([right, left], panes)
	def test_defaults_to_first_pane_without_focus(self):
		left, right = _FakePane(), _FakePane()
		plugin_support = _FakePluginSupport([left, right], active=None)
		panes = panes_active_first(plugin_support, _FakeMainWindow(None))
		self.assertEqual([left, right], panes)

class BringToFrontTest(TestCase):
	def test_restores_minimized_window_without_clearing_maximized_state(self):
		window = _WindowState(Qt.WindowMinimized | Qt.WindowMaximized)

		bring_to_front(window)

		self.assertEqual(Qt.WindowMaximized, window.state)
		self.assertEqual(['show', 'raise', 'activate'], window.calls)

class _FakeWidget:
	def __init__(self):
		self._children = set()
	def add_child(self, widget):
		self._children.add(widget)
	def isAncestorOf(self, widget):
		return widget in self._children

class _FakePluginSupport:
	def __init__(self, panes, active=None):
		self._panes = panes
		self._active = active
	def get_panes(self):
		return self._panes
	def get_active_pane(self):
		return self._active

class _FakeMainWindow:
	def __init__(self, focus_widget):
		self._focus_widget = focus_widget
	def focusWidget(self):
		return self._focus_widget

class _WindowState:
	def __init__(self, state):
		self.state = state
		self.calls = []
	def windowState(self):
		return self.state
	def setWindowState(self, state):
		self.state = state
	def show(self):
		self.calls.append('show')
	def raise_(self):
		self.calls.append('raise')
	def activateWindow(self):
		self.calls.append('activate')

class _FakeFs:
	def __init__(self, dirs=(), files=()):
		self._dirs = set(dirs)
		self._files = set(files)
	def is_dir(self, url):
		if url in self._dirs:
			return True
		if url in self._files:
			return False
		raise FileNotFoundError(url)
	def exists(self, url):
		return url in self._dirs or url in self._files

class _FakePane:
	def __init__(self):
		self.location = None
		self.callback = None
		self.cursor_url = None
		self.commands = []
		self._widget = _FakeWidget()
		self.child_widget = _FakeWidget()
		self._widget.add_child(self.child_widget)
	def set_path(self, location, callback=None):
		self.location = location
		self.callback = callback
	def place_cursor_at(self, url):
		self.cursor_url = url
	def run_command(self, command):
		self.commands.append((command,))
	def focus(self):
		pass

class _RecordingSessionManager:
	def __init__(self):
		self.opened = []
	def open_path_in_pane(self, pane, path):
		self.opened.append((path, pane))

class _RecordingErrorHandler:
	def __init__(self):
		self.reported = []
	def report(self, msg, exc=False):
		self.reported.append(msg)
