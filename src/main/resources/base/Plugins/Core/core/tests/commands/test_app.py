from core.commands.app import About
from core.tests.commands import FakeWindow
from fman import APP_NAME, FMAN_VERSION
from unittest import TestCase
from unittest.mock import patch

class AboutTest(TestCase):
	def test_about_shows_version_and_credits_maintainer_and_original_author(self):
		with patch('core.commands.app.show_alert') as show_alert:
			About(FakeWindow())()

		message = show_alert.call_args.args[0]
		self.assertIn(APP_NAME + ' version: ' + FMAN_VERSION, message)
		self.assertIn(
			'Maintained by Benjamin Kobjolke.\n\nBased on fman by Michael Herrmann.',
			message
		)
