"""Demo 26 captures native Windows Properties dialogs on screen.

It uses screen stills because Properties is a native window; mouse and
multi-monitor placement cases remain a manual check.
"""

from automated_screenshot_connector import DemoScript, Pause, PressKey

from fman.impl.demo import CloseNativeDialogs, ScreenStill


PROPERTIES_CLIPS = {
	26: DemoScript(
		id=26,
		name='properties',
		steps=(
			Pause(1.5),
			PressKey('Down'), PressKey('Down'), PressKey('Down'), PressKey('Down'),
			PressKey('Alt+Enter'),
			Pause(5.0), ScreenStill('properties-file'),
			CloseNativeDialogs(), Pause(1.0),
			PressKey('Home'),
			PressKey('Ins'), PressKey('Ins'), PressKey('Ins'), PressKey('Up'),
			PressKey('Alt+Enter'),
			Pause(6.0), ScreenStill('properties-cascade'),
			CloseNativeDialogs(), Pause(1.0),
			PressKey('Ctrl+D'), PressKey('End'), PressKey('Alt+Enter'),
			Pause(5.0), ScreenStill('properties-bottom-edge'),
			CloseNativeDialogs(), Pause(1.0),
		),
	),
}
