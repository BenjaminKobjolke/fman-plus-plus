"""Record thumbnail view in demo 31.

The left pane holds the ten JPEGs, ``dummy.mp4`` and the example text files.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot,
)


THUMBNAIL_CLIPS = {
	31: DemoScript(
		id=31,
		name='thumbnail-view',
		steps=(
			Pause(1.5),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle thumbnail'), Pause(3.0),
			Screenshot('thumbnail-grid'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('increase font'), Pause(6.0),
			Screenshot('thumbnail-larger'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle thumbnail'), Pause(1.2),
			Screenshot('thumbnail-off'), Pause(1.0),
		),
	),
}
