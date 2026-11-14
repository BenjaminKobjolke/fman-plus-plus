"""Enforce readable dimensions for isolated UI driver windows and captures."""

import struct


MIN_WIDTH = 1280
MIN_HEIGHT = 768
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
WINDOW_PATH = '/v1/window'
SCREENSHOT_PATH = '/v1/screenshot'


def png_size(data: bytes) -> tuple[int, int]:
	if (
		len(data) < 24
		or data[:8] != PNG_SIGNATURE
		or data[12:16] != b'IHDR'
	):
		raise RuntimeError('Screenshot response is not a valid PNG.')
	return struct.unpack('>II', data[16:24])


def ensure_window_size(session, api) -> dict:
	result = api(session, 'POST', WINDOW_PATH, {
		'width': MIN_WIDTH, 'height': MIN_HEIGHT,
	})
	result = dict(result)
	if result['width'] < MIN_WIDTH or result['height'] < MIN_HEIGHT:
		result['window_warning'] = (
			'The window is %sx%s, below the %sx%s minimum; '
			'the usable screen area is %sx%s.' % (
				result['width'], result['height'], MIN_WIDTH, MIN_HEIGHT,
				result['available_width'], result['available_height'],
			)
		)
	return result


def capture_screenshot(session, api) -> bytes:
	data = api(session, 'GET', SCREENSHOT_PATH)
	width, height = png_size(data)
	window = None
	if width < MIN_WIDTH or height < MIN_HEIGHT:
		window = ensure_window_size(session, api)
		data = api(session, 'GET', SCREENSHOT_PATH)
		width, height = png_size(data)
	if width < MIN_WIDTH or height < MIN_HEIGHT:
		available_width = window['available_width']
		available_height = window['available_height']
		raise RuntimeError(
			'Screenshot is %sx%s, below the %sx%s minimum; '
			'the usable screen area is %sx%s.' % (
				width, height, MIN_WIDTH, MIN_HEIGHT,
				available_width, available_height,
			)
		)
	return data
