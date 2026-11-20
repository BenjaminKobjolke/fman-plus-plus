"""Demo 34 shows six columns competing for width in a narrow file pane.

The demo plugin is seeded by run_fman_demo.bat for this recording only.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot,
)


NARROW_COLUMNS_CLIPS = {
	34: DemoScript(
		id=34,
		name='narrow-pane-columns',
		steps=(
			Pause(1.5), Screenshot('narrow-columns-equal'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('set pane sizes'), Pause(1.2),
			Command('25'), Pause(1.5),
			Screenshot('narrow-columns-25'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('narrow active pane'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('narrow active pane'), Pause(1.2),
			Screenshot('narrow-columns-15'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('set pane sizes'), Pause(1.2),
			Command('equal'), Pause(1.5),
			Screenshot('narrow-columns-restored'), Pause(1.2),
		),
	),
}
