"""Record archive browsing and numeric sorting in demo 30.

The seeded left pane holds an ``old.zip`` folder containing ``inner.zip``; the
right pane holds ``deep.zip`` and the four numbered files. Directories sort
first, so the cursor starts on the ``old.zip`` folder and on ``deep.zip`` in
the right pane.
"""

from automated_screenshot_connector import DemoScript, Pause, PressKey, Screenshot


ARCHIVE_CLIPS = {
	30: DemoScript(
		id=30,
		name='archive-sorting',
		steps=(
			Pause(1.5), Screenshot('archive-sorting-panes'),
			PressKey('Return'), Pause(1.5), Screenshot('archive-named-folder'),
			PressKey('Return'), Pause(2.5),
			Screenshot('archive-inside-archive-named-folder'),
			PressKey('Tab'), Pause(0.6), PressKey('Return'), Pause(2.5),
			Screenshot('archive-deep-root'),
			PressKey('Return'), Pause(2.0),
			PressKey('Return'), Pause(2.0),
			PressKey('Return'), Pause(2.0),
			PressKey('Return'), Pause(2.0),
			Screenshot('archive-deep-leaf'), Pause(1.0),
		),
	),
}
