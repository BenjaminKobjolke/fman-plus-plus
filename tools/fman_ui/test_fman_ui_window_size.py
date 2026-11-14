"""Tests for minimum window sizing and screenshot verification."""

import struct
from pathlib import Path
from tempfile import TemporaryDirectory
import zlib
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from dispatch import dispatch
from window_size import (
	MIN_HEIGHT, MIN_WIDTH, capture_screenshot, ensure_window_size, png_size,
)


class WindowSizeTest(TestCase):
	def test_png_size_reads_dimensions_from_a_png(self):
		self.assertEqual((1, 1), png_size(_tiny_png()))

	def test_png_size_rejects_non_png_data(self):
		with self.assertRaisesRegex(RuntimeError, 'PNG'):
			png_size(b'not a PNG')

	def test_capture_accepts_an_image_at_the_minimum_without_resizing(self):
		image = _png(MIN_WIDTH, MIN_HEIGHT)
		api = Mock(return_value=image)

		self.assertEqual(image, capture_screenshot({}, api))
		api.assert_called_once_with({}, 'GET', '/v1/screenshot')

	def test_capture_resizes_once_and_returns_the_second_image(self):
		first = _png(512, 244)
		second = _png(MIN_WIDTH, MIN_HEIGHT)
		api = Mock(side_effect=[first, {
			'width': MIN_WIDTH, 'height': MIN_HEIGHT,
			'available_width': 1920, 'available_height': 1080,
		}, second])

		self.assertEqual(second, capture_screenshot({}, api))
		self.assertEqual(3, api.call_count)
		self.assertEqual(('POST', '/v1/window', {
			'width': MIN_WIDTH, 'height': MIN_HEIGHT,
		}), api.call_args_list[1].args[1:])

	def test_capture_retries_when_image_is_wide_but_too_short(self):
		api = Mock(side_effect=[_png(2000, 700), {
			'width': MIN_WIDTH, 'height': MIN_HEIGHT,
			'available_width': 2000, 'available_height': 1200,
		}, _png(MIN_WIDTH, MIN_HEIGHT)])

		self.assertEqual((MIN_WIDTH, MIN_HEIGHT), png_size(
			capture_screenshot({}, api)))
		self.assertEqual(3, api.call_count)

	def test_capture_reports_both_sizes_when_retry_is_still_small(self):
		api = Mock(side_effect=[_png(512, 244), {
			'width': 1000, 'height': 700,
			'available_width': 1000, 'available_height': 700,
		}, _png(1000, 700)])

		with self.assertRaisesRegex(
			RuntimeError,
			r'Screenshot is 1000x700, below the 1280x768 minimum; '
			r'the usable screen area is 1000x700',
		):
			capture_screenshot({}, api)

	def test_ensure_window_size_warns_only_when_below_the_minimum(self):
		api = Mock(return_value={
			'width': 1280, 'height': 768,
			'available_width': 1920, 'available_height': 1080,
		})
		self.assertNotIn('window_warning', ensure_window_size({}, api))

		api.return_value = {
			'width': 1000, 'height': 700,
			'available_width': 1000, 'available_height': 700,
		}
		result = ensure_window_size({}, api)
		self.assertIn('1280x768', result['window_warning'])

	def test_dispatch_saves_only_verified_png_and_returns_its_dimensions(self):
		image = _png(MIN_WIDTH, MIN_HEIGHT)
		with TemporaryDirectory() as temp:
			path = Path(temp) / 'capture.png'
			with patch('dispatch.guard_input', return_value={}):
				result = dispatch(
					SimpleNamespace(action='screenshot', png_path=str(path)), {},
					Mock(return_value=image), lambda _milliseconds: None)
			self.assertEqual((MIN_WIDTH, MIN_HEIGHT), (
				result['width'], result['height']))
			self.assertEqual(image, path.read_bytes())

	def test_dispatch_does_not_write_an_undersized_capture(self):
		api = Mock(side_effect=[_png(512, 244), {
			'width': 1000, 'height': 700,
			'available_width': 1000, 'available_height': 700,
		}, _png(1000, 700)])
		with TemporaryDirectory() as temp:
			path = Path(temp) / 'capture.png'
			with patch('dispatch.guard_input', return_value={}):
				with self.assertRaisesRegex(RuntimeError, 'usable screen area'):
					dispatch(SimpleNamespace(
						action='screenshot', png_path=str(path)), {}, api,
						lambda _milliseconds: None)
			self.assertFalse(path.exists())


def _tiny_png():
	return _png(1, 1)


def _png(width, height):
	def chunk(name, data):
		return (struct.pack('>I', len(data)) + name + data
			+ struct.pack('>I', zlib.crc32(name + data) & 0xffffffff))

	return (
		b'\x89PNG\r\n\x1a\n'
		+ chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
		+ chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00'))
		+ chunk(b'IEND', b'')
	)
