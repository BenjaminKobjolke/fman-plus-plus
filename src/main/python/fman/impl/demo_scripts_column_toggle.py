"""Stills for the plugin-owned column visibility command demo."""

from automated_screenshot_connector import (
	DemoScript, Pause, PressKey, Screenshot, TypeText,
)

from fman.impl.demo import ExpectChildWindow, LaunchFman, ScreenStill


COLUMN_TOGGLE_CLIPS = {
	32: DemoScript(
		id=32,
		name='plugin-column-toggle',
		steps=(
			Pause(1.5), Screenshot('column-shown'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('toggle demo tag', char_delay_ms=100), Pause(0.5),
			Screenshot('column-palette-entry'), PressKey('Return'),
			Pause(1.5), Screenshot('column-hidden-by-plugin'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('toggle demo tag', char_delay_ms=100), Pause(0.5),
			PressKey('Return'), Pause(1.5),
			Screenshot('column-shown-again'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('toggle demo tag', char_delay_ms=100), Pause(0.5),
			PressKey('Return'), Pause(1.5),
			LaunchFman(('--new-instance', 'after-restart')),
			ExpectChildWindow('after-restart'), Pause(2.0),
			ScreenStill('column-hidden-after-restart'), Pause(1.0),
		),
	),
}
