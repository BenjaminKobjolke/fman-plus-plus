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


def minimum_size(session) -> tuple[int, int]:
	requested = session.get('requested_window')
	if requested is None:
		return MIN_WIDTH, MIN_HEIGHT
	return (
		min(MIN_WIDTH, requested['width']),
		min(MIN_HEIGHT, requested['height']),
	)


def ensure_window_size(session, api) -> dict:
	min_width, min_height = minimum_size(session)
	result = api(session, 'POST', WINDOW_PATH, {
		'width': min_width, 'height': min_height,
	})
	result = dict(result)
	if result['width'] < min_width or result['height'] < min_height:
		result['window_warning'] = (
			'The window is %sx%s, below the %sx%s minimum; '
			'the usable screen area is %sx%s.' % (
				result['width'], result['height'], min_width, min_height,
				result['available_width'], result['available_height'],
			)
		)
	return result


def capture_screenshot(session, api) -> bytes:
	min_width, min_height = minimum_size(session)
	data = api(session, 'GET', SCREENSHOT_PATH)
	width, height = png_size(data)
	window = session.get('window')
	if window is not None and (
		width < window['width'] or height < window['height']
	):
		return data
	window = None
	if width < min_width or height < min_height:
		window = ensure_window_size(session, api)
		data = api(session, 'GET', SCREENSHOT_PATH)
		width, height = png_size(data)
	if width < min_width or height < min_height:
		available_width = window['available_width']
		available_height = window['available_height']
		raise RuntimeError(
			'Screenshot is %sx%s, below the %sx%s minimum; '
			'the usable screen area is %sx%s.' % (
				width, height, min_width, min_height,
				available_width, available_height,
			)
		)
	return data
