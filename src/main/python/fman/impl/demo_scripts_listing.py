"""Stills of the file list for the automated screenshot check.

Demo 15 holds pane listing stills so the screenshot check can judge changes to
how the file list looks. It hides and restores the pane location bars, then
hides them again and takes a still of a second fman started on the same
profile; run_fman_demo.bat starts it with them visible.

It also turns file coloring on for two stills and off again. The profile's
Plugins folder is wiped per launch, so the setting never persists.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot, TypeText,
)
from fman.impl.demo import ExpectChildWindow, LaunchFman, ScreenStill

LISTING_CLIPS = {
	15: DemoScript(
		id=15,
		name='listing',
		steps=(
			Pause(1.5),
			Screenshot('listing-panes'),
			PressKey('Ctrl+Shift+P'),
			Pause(0.6),
			Command('toggle file age shading'),
			Pause(1.5),
			Screenshot('listing-file-age'),
			PressKey('Ctrl+Shift+P'),
			Pause(0.6),
			Command('toggle file age shading'),
			Pause(2.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle file coloring'), Pause(1.5),
			Screenshot('listing-file-colors'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle file age shading'), Pause(1.5),
			Screenshot('listing-file-colors-with-age'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle file age shading'), Pause(1.5),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle file coloring'), Pause(2.2),
			PressKey('Ctrl+Shift+P'),
			Pause(0.6),
			TypeText('toggle pane location bars', char_delay_ms=100),
			Pause(0.5), PressKey('Return'),
			Pause(1.5),
			Screenshot('listing-location-bars-hidden'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('toggle pane location bars', char_delay_ms=100),
			Pause(0.5), PressKey('Return'),
			Pause(1.5),
			Screenshot('listing-location-bars-shown'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('toggle pane location bars', char_delay_ms=100),
			Pause(0.5), PressKey('Return'), Pause(1.5),
			# This same-profile child stands in for restart; later keys would go to it.
			LaunchFman(('--new-instance', 'after-restart')),
			ExpectChildWindow('after-restart'), Pause(2.0),
			ScreenStill('listing-location-bars-after-restart'),
			Pause(1.0),
		),
	),
}
