"""Stills for DemoDropClaim and its two seeded files."""

from automated_screenshot_connector import (
	DemoScript, Pause, PressKey, Screenshot,
)

from fman.impl.demo_drop import DropCursorFile


DROP_CLIPS = {
	29: DemoScript(
		id=29,
		name='plugin-drop-claim',
		steps=(
			Pause(1.5), Screenshot('drop-before'),
			DropCursorFile(), Pause(2.0),
			Screenshot('drop-claimed-by-plugin'),
			PressKey('Down'), Pause(0.6), DropCursorFile(), Pause(1.8),
			Screenshot('drop-default-copy-prompt'),
			PressKey('Return'), Pause(2.0),
			Screenshot('drop-default-copied'), Pause(1.0),
		),
	),
}
