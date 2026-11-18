from fman.impl.view.thumbnail_settings import (
	LOCATIONS_EVERYWHERE, LOCATIONS_LOCAL, PREVIEWS_IMAGES,
	PREVIEWS_WINDOWS, ThumbnailSettings,
)
from unittest import TestCase
from unittest.mock import patch


class ThumbnailSettingsTest(TestCase):

	def test_image_extensions_are_case_insensitive(self):
		settings = ThumbnailSettings(image_extensions=('.png', '.webp'))

		self.assertEqual('image', settings.wants_preview('file://C:/photo.PNG'))

	def test_non_image_files_use_shell_previews_only_when_enabled_on_windows(self):
		settings = ThumbnailSettings(previews=PREVIEWS_WINDOWS)

		with patch('fman.impl.view.thumbnail_settings.PLATFORM', 'Windows'):
			self.assertEqual('shell', settings.wants_preview('file://C:/movie.mp4'))
		with patch('fman.impl.view.thumbnail_settings.PLATFORM', 'Linux'):
			self.assertIsNone(settings.wants_preview('file://C:/movie.mp4'))

	def test_local_location_policy_excludes_archive_images(self):
		settings = ThumbnailSettings(image_extensions=('.png',))

		self.assertEqual('image', settings.wants_preview('file://C:/photo.png'))
		self.assertIsNone(settings.wants_preview('zip://C:/photos.zip/photo.png'))

	def test_everywhere_policy_includes_archive_images(self):
		settings = ThumbnailSettings(
			locations=LOCATIONS_EVERYWHERE, image_extensions=('.png',)
		)

		self.assertEqual(
			'image', settings.wants_preview('zip://C:/photos.zip/photo.png')
		)

	def test_shell_previews_require_local_urls_even_everywhere(self):
		settings = ThumbnailSettings(
			previews=PREVIEWS_WINDOWS, locations=LOCATIONS_EVERYWHERE
		)

		with patch('fman.impl.view.thumbnail_settings.PLATFORM', 'Windows'):
			self.assertIsNone(settings.wants_preview('zip://C:/files.zip/readme.pdf'))
			self.assertEqual(
				'shell', settings.wants_preview('file://C:/docs/readme.pdf')
			)

	def test_images_only_policy_does_not_use_shell_for_local_files(self):
		settings = ThumbnailSettings(
			previews=PREVIEWS_IMAGES, image_extensions=('.png',)
		)

		with patch('fman.impl.view.thumbnail_settings.PLATFORM', 'Windows'):
			self.assertIsNone(settings.wants_preview('file://C:/docs/readme.pdf'))
