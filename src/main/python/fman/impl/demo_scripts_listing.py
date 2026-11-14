"""Stills of the file list for the automated screenshot check.

Demo 15 holds pane listing stills so the screenshot check can judge changes to
how the file list looks. It hides and restores the pane location bars, then
hides them again and takes a still of a second fman started on the same
profile; run_fman_demo.bat starts it with them visible.

It also turns file coloring on for two stills and off again. The profile's
Plugins folder is wiped per launch, so the setting never persists.

Demo 23 shows file coloring in the starting theme and five named themes.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot, TypeText,
)
from fman.impl.demo import ExpectChildWindow, LaunchFman, ScreenStill

FILE_COLOR_THEMES = (
	'Light', 'Solarized Light', 'Windows 11 Light', 'High Contrast', 'Matrix',
)


def select_theme_steps(name, hold_s):
	return (
		PressKey('Ctrl+Shift+P'), Pause(0.6),
		Command('select theme'), Pause(1.2),
		Command(name), Pause(hold_s),
	)


def listing_theme_colors_steps():
	steps = [
		Pause(1.5),
		PressKey('Ctrl+Shift+P'), Pause(0.6),
		Command('opacity'), Pause(1.2),
		Command('100'), Pause(1.2),
		PressKey('Ctrl+Shift+P'), Pause(0.6),
		Command('toggle pane location bars'), Pause(1.5),
		PressKey('Ctrl+Shift+P'), Pause(0.6),
		Command('toggle status bar'), Pause(1.5),
		PressKey('Ctrl+Shift+P'), Pause(0.6),
		Command('toggle file coloring'), Pause(1.5),
		PressKey('Down'), Pause(0.5),
		Screenshot('theme-colors-start'),
	]
	for name in FILE_COLOR_THEMES:
		steps.extend((
			*select_theme_steps(name, 2.5),
			Screenshot(f'theme-colors-{name}'), Pause(1.2),
		))
	return tuple(steps)


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
	23: DemoScript(
		id=23,
		name='listing-theme-colors',
		steps=listing_theme_colors_steps(),
	),
}
