"""Demo 26 captures native Windows Properties dialogs on screen.

It uses screen stills because Properties is a native window; mouse and
multi-monitor placement cases remain a manual check. The recorder pins fman
topmost, so each still raises its shell dialog and holds it for a second.
"""

from automated_screenshot_connector import DemoScript, Pause, PressKey

from fman.impl.demo import (
	CloseNativeDialogs, RaiseNativeDialogs, ScreenStill,
)


PROPERTIES_CLIPS = {
	26: DemoScript(
		id=26,
		name='properties',
		steps=(
			Pause(1.5),
			PressKey('Down'), PressKey('Down'), PressKey('Down'), PressKey('Down'),
			PressKey('Alt+Enter'),
			# Keep dialogs open; the recorder captures stills on its next frame.
			Pause(5.0), RaiseNativeDialogs(), ScreenStill('properties-file'),
			Pause(1.0), CloseNativeDialogs(), Pause(1.0),
			PressKey('Home'),
			PressKey('Ins'), PressKey('Ins'), PressKey('Ins'), PressKey('Up'),
			PressKey('Alt+Enter'),
			Pause(6.0), RaiseNativeDialogs(), ScreenStill('properties-cascade'),
			Pause(1.0), CloseNativeDialogs(), Pause(1.0),
			PressKey('Ctrl+D'), PressKey('End'), PressKey('Alt+Enter'),
			Pause(5.0), RaiseNativeDialogs(), ScreenStill('properties-bottom-edge'),
			Pause(1.0), CloseNativeDialogs(), Pause(1.0),
		),
	),
}
