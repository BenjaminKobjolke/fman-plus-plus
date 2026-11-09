from unittest import TestCase
from unittest.mock import Mock, patch

import fman


class PublicApiTest(TestCase):
	def test_show_alert_forwards_button_texts(self):
		ui = Mock()
		button_texts = {fman.YES: 'Delete'}

		with patch('fman._get_ui', return_value=ui):
			fman.show_alert(
				'msg', fman.YES | fman.NO, fman.YES, button_texts=button_texts
			)

		ui.show_alert.assert_called_once_with(
			'msg', fman.YES | fman.NO, fman.YES, button_texts=button_texts
		)

	def test_show_alert_defaults_button_texts_to_none(self):
		ui = Mock()

		with patch('fman._get_ui', return_value=ui):
			fman.show_alert('msg')

		ui.show_alert.assert_called_once_with(
			'msg', fman.OK, fman.OK, button_texts=None
		)
