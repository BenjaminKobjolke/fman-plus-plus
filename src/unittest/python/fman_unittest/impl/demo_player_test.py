"""Qt event tests for screenshots uploaded by demo playback."""

from importlib.util import find_spec
from unittest import TestCase
from unittest.mock import MagicMock, patch
import unittest

from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication, QWidget

from fman.impl.scripting.automation import AutomationActions

CONNECTOR_AVAILABLE = find_spec('automated_screenshot_connector') is not None
if CONNECTOR_AVAILABLE:
	from automated_screenshot_connector import DemoClient
	from automated_screenshot_connector.steps import DemoScript, SendScreenshot
	from fman.impl.demo import DemoPlayer


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
		)

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
