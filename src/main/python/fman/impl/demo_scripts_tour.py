"""The chapters of the README's feature tour, keyed by ``--automation-demo``.

Split out of ``demo_scripts.py`` to stay under the project's 300-line limit;
that module still owns the registry these are merged into, the overview demo
and the themes builder. See ``docs/DEMOS.md`` for how to record them.

They are recorded separately and joined by
``tools/create_media/build_tour.py``, because the recorder holds every frame
in RAM (~30 MB per second at 10 fps) and aborts a single demo at 300 s. They
emit no ``Screenshot`` steps on purpose: those only write PNG stills, which
the tour doesn't need, and the tool's no-event watchdog is satisfied by
``demo_started`` alone at these lengths.

Every ``Down`` count here is written against the seeded pane order documented
in ``demo_scripts``; ``run_fman_demo.bat`` gives each id >= 3 its own scratch
copy of it.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, TypeText,
)
from fman import APP_NAME

TOUR_CHAPTERS = {
	3: DemoScript(
		id=3,
		name='tour-a-panes',
		steps=(
			Pause(1.5),
			PressKey('Down'), Pause(0.5),
			PressKey('Down'), Pause(0.5),
			PressKey('Down'), Pause(0.5),
			PressKey('Down'), Pause(0.8),
			# Insert selects and advances - the orthodox file-manager key.
			PressKey('Ins'), Pause(0.6),
			PressKey('Ins'), Pause(0.6),
			PressKey('Ins'), Pause(1.2),
			PressKey('Ctrl+D'), Pause(1.0),   # deselect again
			PressKey('Ctrl+A'), Pause(1.4),   # ... and select everything
			PressKey('F5'), Pause(1.8),       # Copy, prefilled with the right pane
			PressKey('Return'), Pause(4.0),   # ~20 MB, dummy.mp4 included
			PressKey('Ctrl+D'), Pause(1.0),
			PressKey('Tab'), Pause(1.2),      # over to the copies
			PressKey('Ctrl+R'), Pause(1.5),   # re-list, so the filter sees them
			TypeText('dummy_1'), Pause(1.8),  # inline type-to-filter
			PressKey('Escape'), Pause(1.0),
			TypeText('read'), Pause(1.8),
			PressKey('Escape'), Pause(1.0),
			PressKey('Ctrl+F2'), Pause(1.8),  # sort by size
			PressKey('Ctrl+F1'), Pause(1.4),  # back to name
			PressKey('Tab'), Pause(1.2),
		),
	),
	4: DemoScript(
		id=4,
		name='tour-b-organize',
		steps=(
			Pause(1.5),
			PressKey('F7'), Pause(1.8),       # prompt prefilled with the stem
			TypeText('documents'), Pause(1.0),
			PressKey('Return'), Pause(1.6),   # created, cursor placed on it
			PressKey('Down'), Pause(0.6),
			PressKey('Ins'), Pause(0.6),
			PressKey('Ins'), Pause(0.6),
			PressKey('Ins'), Pause(1.2),      # the three text files
			PressKey('F6'), Pause(1.8),
			# A bare name in the Move prompt resolves against the SOURCE pane,
			# and the target already exists as a directory, so moving into it
			# needs no further confirmation.
			TypeText('documents'), Pause(1.0),
			PressKey('Return'), Pause(2.5),
			PressKey('Home'), Pause(0.8),     # directories sort first
			PressKey('Return'), Pause(1.8),   # step into it
			PressKey('Shift+F6'), Pause(1.6), # inline editor, extension kept
			TypeText('history'), Pause(1.0),
			PressKey('Return'), Pause(1.8),
			PressKey('Backspace'), Pause(2.0),
			Pause(1.0),
		),
	),
	5: DemoScript(
		id=5,
		name='tour-c-viewers',
		steps=(
			Pause(1.2),
			PressKey('Down'), Pause(0.35),
			PressKey('Down'), Pause(0.35),
			PressKey('Down'), Pause(0.35),
			PressKey('Down'), Pause(0.8),     # dummy_1.jpg
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('view file'), Pause(2.2),
			PressKey('Alt+Up'), Pause(0.7),
			PressKey('Alt+Up'), Pause(1.4),
			# Ctrl+Shift+P inside a viewer opens that viewer's OWN palette -
			# the global one can't reach a viewer while the list is hidden.
			PressKey('Ctrl+Shift+P'), Pause(1.2),
			Command('next'), Pause(2.2),      # on to dummy_2.jpg
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('fit'), Pause(1.4),       # Fit to window, clears the saved zoom
			PressKey('Escape'), Pause(1.2),
			PressKey('Home'), Pause(0.8),     # changelog.txt
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('view file'), Pause(2.0),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('edit'), Pause(1.0),
			PressKey('Ctrl+End'), Pause(0.5),
			PressKey('Return'), Pause(0.3),   # a newline; TypeText can't carry one
			TypeText('Edited in ' + APP_NAME), Pause(1.3),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('save'), Pause(1.5),      # straight to disk, no dialog
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('exit'), Pause(1.2),      # Escape doesn't close in edit mode
		),
	),
	6: DemoScript(
		id=6,
		name='tour-d-video',
		steps=(
			Pause(1.2),
			PressKey('Down'), Pause(0.3),
			PressKey('Down'), Pause(0.3),
			PressKey('Down'), Pause(0.8),     # dummy.mp4
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('view file'), Pause(3.5), # libmpv embeds, then plays
			Pause(1.5),
			PressKey('Space'), Pause(1.6),    # pause
			PressKey('Space'), Pause(1.4),    # play
			PressKey('Right'), Pause(1.0),    # seek +5 s
			PressKey('Right'), Pause(1.0),
			PressKey('Up'), Pause(1.4),       # volume +5, with mpv's OSD
			PressKey('Escape'), Pause(1.2),
			# The same viewer, but in the OTHER pane: the list stays usable,
			# so arrowing down keeps previewing.
			PressKey('Down'), Pause(0.6),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('view in other'), Pause(3.0),
			PressKey('Down'), Pause(1.5),
			PressKey('Down'), Pause(1.5),
			Pause(1.2),
		),
	),
	7: DemoScript(
		id=7,
		name='tour-e-archives',
		steps=(
			Pause(1.2),
			PressKey('Down'), Pause(0.35),
			PressKey('Down'), Pause(0.35),
			PressKey('Down'), Pause(0.35),
			PressKey('Down'), Pause(0.8),
			PressKey('Ins'), Pause(0.6),
			PressKey('Ins'), Pause(0.6),
			PressKey('Ins'), Pause(1.2),      # dummy_1..3.jpg
			PressKey('Alt+F5'), Pause(1.8),   # Pack, suggesting the right pane
			# Replace the whole suggestion: a bare name keeps the archive here,
			# so extracting it into the empty right pane can't hit a conflict.
			PressKey('Ctrl+A'), Pause(0.5),
			TypeText('images.zip'), Pause(1.0),
			PressKey('Return'), Pause(3.5),   # 7-Zip builds it
			# The pane doesn't re-list itself once the archive appears, so the
			# filter below would find nothing without this reload.
			PressKey('Ctrl+R'), Pause(1.5),
			TypeText('ima'), Pause(1.8),      # filter down to the new archive
			PressKey('Return'), Pause(2.5),   # ... and step inside it
			PressKey('F5'), Pause(1.8),       # copy back out of the archive
			PressKey('Return'), Pause(2.5),
			PressKey('Backspace'), Pause(2.0),
			PressKey('Ctrl+Shift+P'), Pause(1.4),
			# Typed as two word-prefixes, to show the palette's fuzzy matching
			# before the command runs.
			TypeText('comp dir'), Pause(2.0),
			PressKey('Return'), Pause(2.0),
			PressKey('Return'), Pause(1.8),   # dismiss the result dialog
			Pause(1.2),
		),
	),
}
