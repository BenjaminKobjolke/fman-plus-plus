"""Qt event tests for screenshots uploaded by demo playback."""

from importlib.util import find_spec
import os
from unittest import TestCase
from unittest.mock import MagicMock, patch
import unittest

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QContextMenuEvent, QImage, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QMenu, QTableView, QWidget

from fman.impl.scripting.automation import AutomationActions

CONNECTOR_AVAILABLE = find_spec('automated_screenshot_connector') is not None
if CONNECTOR_AVAILABLE:
	from automated_screenshot_connector import DemoClient
	from automated_screenshot_connector.steps import (
		CustomStep,
		DemoScript,
		SendScreenshot,
	)
	from fman.impl.demo import (
		DemoPlayer, ExpectChildWindow, ExpectForwarded, LaunchFman,
		OpenContextMenu, ScreenStill,
		WaitForOverwriteQuestion,
	)


@unittest.skipUnless(
	CONNECTOR_AVAILABLE,
	'automated-screenshot-connector is not installed in this environment',
)
class DemoPlayerTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.window = QWidget()
		self.window.setFixedSize(40, 30)
		self.window.show()
		self.addCleanup(self.window.close)

	def _player(self, client, screenshots):
		return DemoPlayer(
			self.window, client,
			DemoScript(id=99, name='test', steps=()), 1, screenshots,
			plugin_support=MagicMock(),
		)

	def test_launch_fman_starts_the_main_script_with_a_resolved_folder(self):
		plugin_support = MagicMock()
		plugin_support.get_panes.return_value = [MagicMock()]
		plugin_support.get_panes.return_value[0].get_path.return_value = 'C:/demo'
		player = DemoPlayer(
			self.window, MagicMock(spec=DemoClient),
			DemoScript(id=99, name='test', steps=()), 1, MagicMock(),
			plugin_support=plugin_support,
		)

		with patch('fman.impl.demo.subprocess.Popen') as popen:
			with patch('fman.impl.demo.sys.executable', 'python.exe'):
				with patch('fman.impl.demo.sys.argv', ['main.py']):
					with patch('fman.impl.demo.os.path.abspath', return_value='main.py'):
						player._launch_fman(LaunchFman(('--new-instance', 'separate')))

		popen.assert_called_once_with([
			'python.exe', 'main.py', '--new-instance',
			os.path.join('C:/demo', 'separate'),
		])
		self.assertEqual([popen.return_value], player._children)

	def test_expect_child_window_waits_until_child_is_foreground(self):
		player = self._player(MagicMock(spec=DemoClient), MagicMock())
		child = MagicMock()
		child.pid = 123
		child.poll.return_value = None
		player._children = [child]

		with patch(
			'fman.impl.demo.foreground_process_window', return_value=True,
		) as foreground:
			with patch.object(player, '_advance') as advance:
				player._expect_child_window(
					ExpectChildWindow('opened-by-new-instance'))

		foreground.assert_called_once_with(123, 'opened-by-new-instance')
		advance.assert_called_once_with()

	def test_expect_child_window_fails_when_child_window_never_appears(self):
		player = self._player(MagicMock(spec=DemoClient), MagicMock())
		child = MagicMock()
		child.pid = 123
		child.poll.return_value = None
		player._children = [child]

		with patch('fman.impl.demo.time.monotonic', side_effect=(0, 1)):
			with patch(
				'fman.impl.demo.foreground_process_window', return_value=False,
			):
				with patch('fman.impl.demo.QTimer.singleShot') as single_shot:
					with patch.object(player, '_fail') as fail:
						player._expect_child_window(
							ExpectChildWindow('missing', timeout_s=0.5))

		fail.assert_called_once_with()
		single_shot.assert_not_called()

	def test_expect_forwarded_advances_when_launch_and_pane_match(self):
		player = self._player(MagicMock(spec=DemoClient), MagicMock())
		old_child, recent_child = MagicMock(), MagicMock()
		old_child.poll.return_value = None
		recent_child.poll.return_value = 0
		player._children = [old_child, recent_child]
		player._plugin_support.get_active_pane.return_value.get_path.return_value = (
			'C:/demo/forwarded'
		)

		with patch('fman.impl.demo.QTimer.singleShot'):
			with patch.object(player, '_advance') as advance:
				player._expect_forwarded(ExpectForwarded('forwarded'))

		advance.assert_called_once_with()

	def test_expect_forwarded_timeout_fails_and_closes_client(self):
		client = MagicMock(spec=DemoClient)
		player = self._player(client, MagicMock())
		child = MagicMock()
		child.poll.return_value = None
		player._children = [child]
		application = MagicMock()

		with patch('fman.impl.demo.time.monotonic', side_effect=(0, 1)):
			with patch('fman.impl.demo.QTimer.singleShot'):
				with patch(
					'fman.impl.demo.QApplication.instance',
					return_value=application,
				):
					player._expect_forwarded(ExpectForwarded('missing', 0.5))

		child.terminate.assert_called_once_with()
		client.close.assert_called_once_with()
		application.quit.assert_called_once_with()

	def test_expect_forwarded_waits_for_earlier_child_to_remain_running(self):
		player = self._player(MagicMock(spec=DemoClient), MagicMock())
		old_child, recent_child = MagicMock(), MagicMock()
		old_child.poll.return_value = 1
		recent_child.poll.return_value = 0
		player._children = [old_child, recent_child]
		player._plugin_support.get_active_pane.return_value.get_path.return_value = (
			'C:/demo/forwarded'
		)

		with patch('fman.impl.demo.time.monotonic', side_effect=(0, 1)):
			with patch('fman.impl.demo.QTimer.singleShot') as single_shot:
				with patch.object(player, '_advance') as advance:
					with patch.object(player, '_fail') as fail:
						player._expect_forwarded(
							ExpectForwarded('forwarded', timeout_s=0.5)
						)

		advance.assert_not_called()
		fail.assert_called_once_with()
		single_shot.assert_not_called()

	def test_expect_forwarded_keeps_waiting_while_no_pane_is_active(self):
		player = self._player(MagicMock(spec=DemoClient), MagicMock())
		child = MagicMock()
		child.poll.return_value = 0
		player._children = [child]
		player._plugin_support.get_active_pane.return_value = None

		with patch('fman.impl.demo.time.monotonic', side_effect=(0, 0)):
			with patch('fman.impl.demo.QTimer.singleShot') as single_shot:
				with patch.object(player, '_advance') as advance:
					player._expect_forwarded(
						ExpectForwarded('forwarded', timeout_s=1)
					)

		advance.assert_not_called()
		single_shot.assert_called_once()

	def test_finish_terminates_a_running_child(self):
		player = self._player(MagicMock(spec=DemoClient), MagicMock())
		child = MagicMock()
		child.poll.return_value = None
		player._children = [child]

		with patch('fman.impl.demo.QApplication.instance', return_value=None):
			player._finish()

		child.terminate.assert_called_once_with()

	def test_screenshot_step_uploads_the_rendered_window(self):
		client = MagicMock(spec=DemoClient)
		player = self._player(client, AutomationActions(self.window, None))

		with patch('fman.impl.demo.QTimer'):
			player._execute(SendScreenshot('still'))

		client.send_screenshot.assert_called_once()
		name, = client.send_screenshot.call_args.args
		png = client.send_screenshot.call_args.kwargs['png']
		self.assertEqual('still', name)
		self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
		image = QImage.fromData(png, 'PNG')
		self.assertFalse(image.isNull())
		self.assertEqual((40, 30), (image.width(), image.height()))

	def test_screenshot_step_uses_the_injected_renderer(self):
		client = MagicMock(spec=DemoClient)
		screenshots = MagicMock(spec=AutomationActions)
		screenshots.screenshot_png.return_value = b'png-bytes'
		player = self._player(client, screenshots)

		with patch('fman.impl.demo.QTimer'):
			player._execute(SendScreenshot('still'))

		screenshots.screenshot_png.assert_called_once_with()
		client.send_screenshot.assert_called_once_with('still', png=b'png-bytes')

	def test_screen_still_asks_the_recording_tool_to_capture_the_screen(self):
		client = MagicMock(spec=DemoClient)
		player = DemoPlayer(
			QObject(), client,
			DemoScript(id=99, name='test', steps=(CustomStep(ScreenStill('x')),)),
			1, MagicMock(spec=AutomationActions), plugin_support=MagicMock(),
		)

		with patch('fman.impl.demo.QTimer'):
			player._execute(CustomStep(ScreenStill('x')))

		client.send_screenshot.assert_called_once_with('x')

	def test_overwrite_wait_captures_only_after_the_question_is_open(self):
		from fman.impl.overwrite_dialog import OverwriteDialog

		client = MagicMock(spec=DemoClient)
		player = self._player(client, MagicMock())
		dialog = OverwriteDialog(self.window, 'Replace?', None)
		dialog.show()
		self.addCleanup(dialog.deleteLater)

		with patch('fman.impl.demo.post_chord') as post_chord:
			with patch('fman.impl.demo.QTimer.singleShot') as single_shot:
				with patch.object(player, '_advance') as advance:
					player._wait_for_overwrite_question(
						WaitForOverwriteQuestion())
					callback = single_shot.call_args.args[1]
					callback()

		client.send_screenshot.assert_called_once_with('ftp-overwrite-question')
		post_chord.assert_called_once_with(dialog, 'Return')
		advance.assert_called_once_with()

	def test_overwrite_wait_timeout_closes_the_recording_session(self):
		client = MagicMock(spec=DemoClient)
		player = self._player(client, MagicMock())
		application = MagicMock()

		with patch('fman.impl.demo.time.monotonic', side_effect=(0, 31)):
			with patch(
				'fman.impl.demo.QApplication.instance', return_value=application,
			):
				player._wait_for_overwrite_question(
					WaitForOverwriteQuestion(timeout_s=30))

		client.close.assert_called_once_with()
		application.quit.assert_called_once_with()

	def test_open_context_menu_posts_a_keyboard_event_at_the_current_row(self):
		view = QTableView(self.window)
		model = QStandardItemModel(2, 1, view)
		view.setModel(model)
		view.setGeometry(0, 0, 40, 30)
		view.show()
		index = model.index(1, 0)
		view.setCurrentIndex(index)
		view.setFocus()
		self.app.processEvents()
		events = []
		filter_ = _ContextMenuEventFilter(events)
		view.viewport().installEventFilter(filter_)
		player = self._player(MagicMock(spec=DemoClient), MagicMock())

		with patch('fman.impl.demo.QTimer'):
			player._execute(CustomStep(OpenContextMenu()))
		self.app.processEvents()

		self.assertEqual(
			events,
			[(QContextMenuEvent.Keyboard, view.visualRect(index).center())],
		)

	def test_keys_go_to_an_open_menu(self):
		player = self._player(MagicMock(spec=DemoClient), MagicMock())
		menu = QMenu(self.window)

		with patch('fman.impl.demo.QApplication.activePopupWidget', return_value=menu):
			self.assertIs(player._target(), menu)
		with patch('fman.impl.demo.QApplication.activePopupWidget', return_value=None):
			with patch(
				'fman.impl.demo.QApplication.focusWidget',
				return_value=self.window,
			):
				self.assertIs(player._target(), self.window)

	def test_open_context_menu_without_an_item_view_raises(self):
		self.window.setFocus()
		player = self._player(MagicMock(spec=DemoClient), MagicMock())

		with patch('fman.impl.demo.QTimer'):
			with self.assertRaisesRegex(ValueError, 'focused file view'):
				player._execute(CustomStep(OpenContextMenu()))


class _ContextMenuEventFilter(QObject):
	def __init__(self, events):
		super().__init__()
		self.events = events

	def eventFilter(self, _watched, event):
		if isinstance(event, QContextMenuEvent):
			self.events.append((event.reason(), event.pos()))
		return False
