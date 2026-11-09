from fman.impl.widgets import LOADING_MESSAGE, LOADING_MESSAGE_NETWORK, \
	format_loading_message, _overlay_pos
from fman.impl.prompt_popup import Prompt
from fman.impl.widgets import MainWindow
from PyQt5.QtCore import QRect, QSize
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog, QLineEdit, QWidget
from unittest import TestCase
from unittest.mock import MagicMock, patch

class PromptTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])
	def test_password_prompt_uses_password_echo_mode(self):
		prompt = Prompt(None, self.app, {}, 'Password:', password=True)
		self.assertEqual(QLineEdit.Password, prompt._query.echoMode())
	def test_prompt_uses_normal_echo_mode_by_default(self):
		prompt = Prompt(None, self.app, {}, 'Name:')
		self.assertEqual(QLineEdit.Normal, prompt._query.echoMode())

class FormatLoadingMessageTest(TestCase):

	"""
	The elapsed seconds are what tell the user the app is still working. A
	message that does not change reads as a freeze.
	"""

	def test_shows_whole_elapsed_seconds(self):
		self.assertIn('(12 s)', format_loading_message(LOADING_MESSAGE, 12.7))
	def test_starts_with_the_title(self):
		text = format_loading_message(LOADING_MESSAGE_NETWORK, 3.0)
		self.assertTrue(text.startswith(LOADING_MESSAGE_NETWORK.title), text)
	def test_detail_is_below_the_title(self):
		title, blank, first_detail_line = \
			format_loading_message(LOADING_MESSAGE, 1.0).split('\n')[:3]
		self.assertEqual(LOADING_MESSAGE.title, title)
		self.assertEqual('', blank)
		self.assertTrue(first_detail_line)

class OverlayPosTest(TestCase):

	"""
	The tutorial overlay used to sit in the center of the window - on top of the
	file list it was asking the user to navigate. It now parks in the bottom
	right corner, clear of the rows and above the status bar.
	"""

	def test_leaves_a_margin_to_the_bottom_right(self):
		pos = _overlay_pos(QSize(1000, 800), QSize(300, 200), 0, margin=20)
		self.assertEqual((680, 580), (pos.x(), pos.y()))
	def test_sits_above_the_status_bar(self):
		pos = _overlay_pos(QSize(1000, 800), QSize(300, 200), 25, margin=20)
		self.assertEqual(555, pos.y())
	def test_stays_on_screen_when_the_overlay_is_larger_than_the_window(self):
		# Clamping to 0 keeps the overlay's top left - and thus the start of its
		# text and its title - visible. Without it, both scroll off screen.
		pos = _overlay_pos(QSize(400, 300), QSize(600, 500), 25, margin=20)
		self.assertEqual((0, 0), (pos.x(), pos.y()))
	def test_a_dialog_that_does_not_overlap_leaves_the_overlay_alone(self):
		# Opening the command palette must not make the overlay jump around.
		pos = _overlay_pos(
			QSize(1000, 800), QSize(300, 200), 0,
			QRect(200, 100, 400, 300), margin=20
		)
		self.assertEqual((680, 580), (pos.x(), pos.y()))
	def test_moves_above_a_dialog_that_would_cover_the_overlay(self):
		# Dialogs are windows of their own, so a covered overlay cannot be
		# raised back into view - it has to move. Above the dialog, not merely
		# to the top margin: the command palette is centered and tall, so it
		# reaches into the top right corner as well.
		pos = _overlay_pos(
			QSize(1000, 800), QSize(300, 200), 0,
			QRect(200, 300, 600, 400), margin=20
		)
		self.assertEqual((680, 80), (pos.x(), pos.y()))
	def test_stays_on_screen_when_a_dialog_leaves_no_room_above(self):
		# Nothing fits anywhere; the top of the window is the least bad place,
		# because it keeps the overlay's title and first lines readable.
		pos = _overlay_pos(
			QSize(1000, 800), QSize(300, 200), 0,
			QRect(200, 100, 700, 650), margin=20
		)
		self.assertEqual((680, 0), (pos.x(), pos.y()))

class ShowPromptCompatTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])
	def test_show_prompt_derives_legacy_result_from_show_input(self):
		class FakeWindow(QWidget):
			def __init__(self, result):
				super().__init__()
				self.result = result
				self.arguments = None
			def show_input(self, *args, **kwargs):
				self.arguments = (args, kwargs)
				return self.result
			def exec_dialog(self, dialog):
				return self.result is not None

		arguments = {
			'default': '', 'selection_start': 1, 'selection_end': 2,
			'get_completions': lambda text: [text], 'password': True
		}
		for input_result, expected in (
			(None, ('', False)), ('', ('', True)), ('ab', ('ab', True))
		):
			with self.subTest(input_result=input_result):
				window = FakeWindow(input_result)
				self.assertEqual(
					expected, MainWindow.show_prompt(window, 'Name:', **arguments)
				)
				self.assertEqual((('Name:',), arguments), window.arguments)


class TitleBarWindowActivationTest(TestCase):
	def test_reactivates_the_window_after_changing_title_bar(self):
		window = MagicMock()
		window.is_title_bar_visible.return_value = True
		window.isVisible.return_value = True
		window.geometry.return_value = QRect(0, 0, 640, 480)
		window.frameGeometry.return_value = QRect(0, 0, 640, 480)
		window.windowOpacity.return_value = 1.0

		MainWindow.set_title_bar_visible.__wrapped__(window, False)

		window.activateWindow.assert_called_once_with()


class ExecDialogTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def _window(self):
		window = QWidget()
		window.before_dialog = MagicMock()
		window._app = self.app
		window._dialog = None
		window._match_title_bar = MagicMock()
		return window

	def test_embeds_dialog_when_no_modal_widget_is_active(self):
		window = self._window()
		dialog = QDialog()
		with patch(
			'fman.impl.widgets.QApplication.activeModalWidget', return_value=None
		), \
				patch(
					'fman.impl.widgets.exec_in_window',
					return_value=QDialog.Accepted
			) as embedded:
			self.assertEqual(
				QDialog.Accepted, MainWindow.exec_dialog.__wrapped__(window, dialog)
			)
		embedded.assert_called_once_with(dialog, window)
		self.assertIsNone(window._dialog)
		window.close()

	def test_show_alert_uses_embedded_dialog_when_no_modal_widget_is_active(self):
		window = self._window()
		window._theme = MagicMock()
		window._app = self.app
		window.before_dialog = MagicMock()
		window._dialog = None
		window._match_title_bar = MagicMock()
		exec_dialog = MainWindow.exec_dialog.__wrapped__
		window.exec_dialog = lambda dialog: exec_dialog(window, dialog)
		with patch(
			'fman.impl.widgets.QApplication.activeModalWidget', return_value=None
		), \
				patch(
					'fman.impl.widgets.exec_in_window',
					return_value=QDialog.Accepted
			) as embedded:
			self.assertEqual(
				QDialog.Accepted,
				MainWindow.show_alert.__wrapped__(
					window, 'Delete this file?'
				)
			)
		embedded.assert_called_once()
		self.assertIs(window, embedded.call_args.args[1])
		window.close()

	def test_modal_fallback_is_frameless_with_either_title_bar_setting(self):
		for visible in (True, False):
			with self.subTest(title_bar_visible=visible):
				window = self._window()
				window._match_title_bar = MagicMock()
				dialog = QDialog()
				dialog.exec = MagicMock(return_value=QDialog.Rejected)
				with patch(
					'fman.impl.widgets.QApplication.activeModalWidget',
					return_value=QDialog()
				), \
						patch('fman.impl.widgets.Scrim'):
					self.assertEqual(
						QDialog.Rejected,
						MainWindow.exec_dialog.__wrapped__(window, dialog)
					)
				self.assertTrue(dialog.windowFlags() & Qt.FramelessWindowHint)
				self.assertTrue(dialog.property('frameless'))
				window.close()
