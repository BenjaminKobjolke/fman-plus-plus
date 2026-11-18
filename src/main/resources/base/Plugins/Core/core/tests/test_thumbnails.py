from core import thumbnails
from core.imageviewer import IMAGE_EXTENSIONS
from core.thumbnails import (
	DEFAULT_PREVIEWS, DEFAULT_LOCATIONS, DEFAULT_SIZE, MAX_SIZE, MIN_SIZE,
)
from unittest import TestCase
from unittest.mock import patch, Mock
from PyQt5.QtWidgets import QApplication


class ThumbnailSettingsTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def test_uses_defaults_when_settings_are_absent(self):
		with patch.object(thumbnails, 'get_setting', return_value=None):
			settings = thumbnails.get_thumbnail_settings()

		self.assertEqual(DEFAULT_SIZE, settings.size)
		self.assertEqual(DEFAULT_PREVIEWS, settings.previews)
		self.assertEqual(DEFAULT_LOCATIONS, settings.locations)
		self.assertEqual(IMAGE_EXTENSIONS, settings.image_extensions)

	def test_uses_defaults_for_invalid_settings(self):
		values = {
			thumbnails.PREVIEWS_KEY: 'invalid',
			thumbnails.LOCATIONS_KEY: 'invalid',
			thumbnails.SIZE_KEY: 'large',
		}
		with patch.object(
			thumbnails, 'get_setting', side_effect=lambda _file, key, _default=None:
				values[key]
		):
			settings = thumbnails.get_thumbnail_settings()

		self.assertEqual(DEFAULT_SIZE, settings.size)
		self.assertEqual(DEFAULT_PREVIEWS, settings.previews)
		self.assertEqual(DEFAULT_LOCATIONS, settings.locations)

	def test_clamps_size_steps_at_both_limits(self):
		self.assertEqual(MIN_SIZE, thumbnails.step_size(MIN_SIZE, -1))
		self.assertEqual(MAX_SIZE, thumbnails.step_size(MAX_SIZE, +1))

	def test_steps_size_by_25_percent(self):
		self.assertEqual(160, thumbnails.step_size(128, +1))
		self.assertEqual(102, thumbnails.step_size(128, -1))

	def test_steps_and_applies_size_to_thumbnail_panes(self):
		thumbnail_pane = Mock()
		thumbnail_pane.is_thumbnail_view.return_value = True
		other_pane = Mock()
		other_pane.is_thumbnail_view.return_value = False
		window = Mock()
		window.get_panes.return_value = [thumbnail_pane, other_pane]

		with patch.object(thumbnails, 'get_setting', return_value=128), \
				patch.object(thumbnails, 'save_setting'):
			size = thumbnails.change_thumbnail_size(window, +1)

		self.assertEqual(160, size)
		thumbnail_pane._widget.set_thumbnail_settings.assert_called_once()
		other_pane._widget.set_thumbnail_settings.assert_not_called()

