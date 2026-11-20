"""Record an active copy's progress dialog in demo 33.

The launcher seeds ``copy-progress`` in the left pane; directories sort first,
so the cursor starts on it. F5 and Return copy it to the empty right pane, and
the copy is cancelled once the progress dialog has been captured.
"""

from automated_screenshot_connector import DemoScript, Pause, PressKey, Screenshot

from fman.impl.demo import ScreenStill


COPY_PROGRESS_CLIPS = {
	33: DemoScript(
		id=33,
		name='copy-progress',
		steps=(
			Pause(1.5), PressKey('F5'), Pause(1.8), PressKey('Return'),
			Pause(3.0), Screenshot('copy-progress-window'),
			Pause(1.0), ScreenStill('copy-progress-screen'),
			PressKey('Escape'), Pause(2.0),
			ScreenStill('copy-progress-canceled'), Pause(1.0),
		),
	),
}
