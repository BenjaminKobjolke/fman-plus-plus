"""Stills for automated screenshot checks of launch and consent behavior."""

from automated_screenshot_connector import (
	DemoScript, Pause, PressKey, Screenshot, TypeText,
)

from fman.impl.demo import (
	ExpectChildWindow, ExpectForwarded, LaunchFman, ScreenStill,
)


LAUNCH_CLIPS = {
	18: DemoScript(
		id=18,
		name='single-instance',
		steps=(
			Pause(1.5),
			Screenshot('single-instance-primary'),
			LaunchFman(('--new-instance', 'opened-by-new-instance')),
			ExpectChildWindow('opened-by-new-instance'),
			Pause(2.0),
			ScreenStill('single-instance-new-window'),
			Pause(1.2),
			LaunchFman(('forwarded-to-original',)),
			ExpectForwarded('forwarded-to-original'),
			Pause(1.5),
			Screenshot('single-instance-forwarded-to-original'),
			Pause(1.0),
		),
	),
	25: DemoScript(
		id=25,
		name='usage-consent',
		steps=(
			Pause(1.5),
			Screenshot('usage-consent-question'),
			# Escape answers No: a recording must never consent to anything.
			PressKey('Escape'), Pause(1.2),
			Screenshot('usage-consent-answered'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('toggle usage statistics'), Pause(1.0),
			Screenshot('usage-statistics-palette'),
			PressKey('Return'), Pause(1.0),
			Screenshot('usage-statistics-toggled'),
			Pause(1.0),
		),
	),
}

LISTENING_DEMO_IDS = frozenset({18})
CONSENT_DEMO_IDS = frozenset({25})
