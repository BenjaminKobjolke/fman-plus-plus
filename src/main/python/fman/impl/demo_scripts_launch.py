"""Stills for the automated screenshot check of single-instance launches."""

from automated_screenshot_connector import DemoScript, Pause, Screenshot

from fman.impl.demo import ExpectForwarded, LaunchFman, ScreenStill


LAUNCH_CLIPS = {
	18: DemoScript(
		id=18,
		name='single-instance',
		steps=(
			Pause(1.5),
			Screenshot('single-instance-primary'),
			LaunchFman(('--new-instance', 'opened-by-new-instance')),
			Pause(10.0),
			ScreenStill('single-instance-new-window'),
			Pause(1.2),
			LaunchFman(('forwarded-to-original',)),
			ExpectForwarded('forwarded-to-original'),
			Pause(1.5),
			Screenshot('single-instance-forwarded-to-original'),
			Pause(1.0),
		),
	),
}

LISTENING_DEMO_IDS = frozenset({18})
