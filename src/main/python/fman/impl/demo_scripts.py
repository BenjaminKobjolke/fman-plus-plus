"""The recordable demo scripts, keyed by ``--automation-demo <id>``.

Split out of ``demo.py`` so the player stays readable next to a registry that
grows with every recorded chapter. See ``docs/DEMOS.md`` for how to record
these and what each one is for.

Both panes are already positioned by the trailing paths on the command line
(``tools/create_media/run_fman_demo.bat``), so a script only drives the UI.
Three things every script here depends on:

- **Pane order.** ``core.Name.get_sort_value`` sorts directories first, then
  case-insensitively and naturally, so the seeded folder reads changelog.txt,
  config.json, data.csv, dummy.mp4, dummy_1..dummy_10.jpg, notes.md,
  readme.md, todo.txt - ``dummy.mp4`` before ``dummy_1.jpg`` because ``.``
  sorts before ``_``. Every ``Down`` count below is written against that.
- **Prompt timing.** ``Prompt`` selects its prefilled text only on its second
  ``paintEvent``, so every step that types into one waits >= 1.6 s first.
- **Return is only ever pressed** on a directory, on a ``.zip`` (which
  ``ArchiveOpenListener`` rewrites into "open directory"), or inside a
  dialog. Pressing it on a ``.jpg``/``.mp4`` would launch the Windows default
  application on top of the recording.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot, TypeText,
)

from fman.impl.demo_scripts_dialogs import DIALOG_CLIPS
from fman.impl.demo_scripts_launch import LAUNCH_CLIPS
from fman.impl.demo_scripts_tour import TOUR_CHAPTERS

# Every recording starts translucent, so fman is shown the way it is meant to
# be used and the overview's opacity chapter has something to move away from.
# Forced in application_context._run_demo rather than read from the demo
# profile: a take must never inherit whatever the recordist last picked.
DEMO_OPACITY = 0.8

# The themes demo has no entry in DEMOS: its steps are built per run from the
# themes that are actually installed, so a new ``Themes/*.json`` reaches the
# recording without an edit here. See ``build_themes_script``.
THEMES_DEMO_ID = 2
# How long a theme stays on screen before its still is taken - and, once the
# stills are joined by tools/create_media/build_themes.py, how long it is on
# screen in the GIF.
THEME_HOLD_S = 2.0

DEMOS = {
	1: DemoScript(
		id=1,
		name='overview',
		steps=(
			Pause(0.8),
			Screenshot('panes'),
			# Preview a file in the OTHER pane with fman's internal viewer,
			# while the left pane's list stays visible. Row 0 sorts to the
			# video; one Down lands on the first image.
			PressKey('Down'), Pause(0.4),
			# Open the palette, then type the command + Return to run it.
			PressKey('Ctrl+Shift+P'), Pause(0.5),
			Command('view in other'),  # palette alias 'View in other pane'
			Pause(1.0),
			Screenshot('view-image'),
			# Inline name filter: typing activates fman's FilterBar.
			TypeText('dummy_1'), Pause(0.6),
			Screenshot('filter'),
			PressKey('Escape'), Pause(0.3),
			# A real command run from the palette: select every file. The
			# still is taken while the palette is open, because the README's
			# feature grid shows the palette itself.
			PressKey('Ctrl+Shift+P'), Pause(0.5),
			Screenshot('command-palette'),
			Command('select all'),
			Pause(0.8),
			Screenshot('select-all'),
			Pause(1.0),
			# Window opacity is palette-only (no default key binding), so the
			# palette is the only way to show it at all. 'Opacity' is an alias
			# of Set window opacity. The window already records at
			# DEMO_OPACITY, so the picker goes the other way first: '100'
			# matches just the '100%' preset, '80' just the '80%' one.
			PressKey('Ctrl+Shift+P'), Pause(0.5),
			Command('opacity'), Pause(1.2),
			Command('100'), Pause(1.8),
			# A few moves at full opacity, so the difference reads in motion
			# and not only in a still frame.
			PressKey('Ctrl+D'), Pause(0.8),
			PressKey('Down'), Pause(0.5),
			PressKey('Down'), Pause(0.5),
			PressKey('Up'), Pause(1.0),
			# ... and back to where the recording started.
			PressKey('Ctrl+Shift+P'), Pause(0.5),
			Command('opacity'), Pause(1.2),
			Command('80'), Pause(1.8),
		),
	),
}

# The tour chapters live in their own module; merged in below so
# ``--automation-demo <id>`` still resolves every demo from one registry.
DEMOS.update(TOUR_CHAPTERS)

# Standalone feature clips for the README's feature index. Deliberately NOT
# named tour-*: build_tour.py picks up every tour-* demo, so a tour-* name here
# would silently lengthen the joined feature tour. tools/demo_build_feature_gifs.bat
# turns these into the committed GIFs under media/demos/features/.
FEATURE_CLIPS = {
	8: DemoScript(
		id=8,
		name='feature-goto',
		steps=(
			Pause(1.5),
			# Ctrl+P is Go to: a fuzzy jump over the folders you have already
			# visited, with tab-completion. run_fman_demo.bat seeds this id's
			# Visited Paths.json with the scratch tree, which is what keeps
			# the suggestion list deterministic - AND keeps the recordist's
			# own folders off camera. See the privacy note in docs/DEMOS.md.
			PressKey('Ctrl+P'), Pause(1.6),
			# Two characters on purpose: SuggestLocations only reaches out to
			# the Windows Search index once the query is LONGER than two, and
			# that index would answer with folders from anywhere on the disk.
			TypeText('re'), Pause(1.8),
			PressKey('Return'), Pause(2.4),   # jump into reports/
			PressKey('Ctrl+P'), Pause(1.6),
			TypeText('al'), Pause(1.8),
			# Tab completes the highlighted suggestion into the input, so the
			# full path is visible before it is opened.
			PressKey('Tab'), Pause(1.6),
			PressKey('Return'), Pause(2.4),   # ... into projects/alpha
			PressKey('Backspace'), Pause(1.8),
			PressKey('Backspace'), Pause(1.8),
			Pause(1.0),
		),
	),
	9: DemoScript(
		id=9,
		name='feature-tail',
		steps=(
			Pause(1.5),
			# service.log sorts second-to-last (todo.txt is last), so End+Up
			# lands on it without counting a dozen Downs.
			PressKey('End'), Pause(0.8),
			PressKey('Up'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('view file'), Pause(2.4),
			# The text viewer's OWN palette. 'tail' matches the entry
			# 'Enable tail mode (follow end)'.
			PressKey('Ctrl+Shift+P'), Pause(1.2),
			Command('tail'), Pause(2.0),
			# run_fman_demo.bat is appending a line every 1.5 s in the
			# background, so this hold is the whole point of the chapter:
			# the view follows the end of the file while it grows.
			Pause(8.0),
			PressKey('Escape'), Pause(1.5),
		),
	),
}

DEMOS.update(FEATURE_CLIPS)

# Demos of a THIRD-PARTY plugin, for the README's plugin list and the plugin's
# own README. Their own prefix, not feature-*: they film software this repo does
# not ship, so they carry a prerequisite no other demo has - the plugin has to be
# installed, and run_fman_demo.bat seeds it back into the wiped demo profile.
# tools/demo_build_plugin_gifs.bat encodes them; see docs/DEMOS_PLUGINS.md.
PLUGIN_CLIPS = {
	10: DemoScript(
		id=10,
		name='plugin-matrix-rain',
		steps=(
			Pause(1.5),
			# MatrixRain has no "both panes" command - only "Matrix rain" (this
			# pane, takes focus) and "Matrix rain in other pane" (focus stays
			# put). Running the other-pane one FIRST is what gives one pane then
			# both, and it also leaves the keyboard in the left file list for
			# every palette step below: MatrixRainView.keyPressEvent swallows
			# Escape/Return/Backspace/Tab, and whether Ctrl+Shift+P reaches
			# Core's palette from inside the mounted rain is untested.
			#
			# Every query here EQUALS one command's alias, so it lands in the
			# palette's exact-match bucket (match_titles_or_keywords, bucket 0)
			# ahead of every fuzzy tier - no shortest-title tie-break involved.
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('matrix rain in other pane'), Pause(2.5),
			Pause(4.0),                        # ... the right pane alone
			# Transparency is 0 in a fresh demo profile (the plugin's settings
			# live under Plugins\User\Settings, which the launcher wipes), so
			# the prompt always opens on the same value.
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('matrix rain transparency'), Pause(1.8),
			PressKey('Ctrl+A'), Pause(0.4),
			TypeText('70'), Pause(0.8),
			# remount_rain_where_showing() re-mounts every raining pane, so the
			# file list underneath shows through without touching that pane.
			PressKey('Return'), Pause(3.0),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('matrix rain'), Pause(2.5),
			Pause(5.0),                        # ... and now both panes
			PressKey('Escape'), Pause(1.5),    # closes this pane's rain only
			PressKey('Tab'), Pause(1.2),
			PressKey('Escape'), Pause(1.5),
			Pause(1.0),
		),
	),
}

DEMOS.update(PLUGIN_CLIPS)

# Dialog stills let the automated visual check judge dialog changes.
DEMOS.update(DIALOG_CLIPS)

# The single-instance launch demo needs the primary process to accept forwards.
DEMOS.update(LAUNCH_CLIPS)

def build_themes_script(names):
	"""The themes demo for the installed themes `names`, one still each.

	Only the stills are used: ``fman.json`` gives this demo no video format,
	and ``build_themes.py`` joins the PNGs into the README's GIF. That is why
	the command palette may be on screen between the holds - nothing but the
	``Screenshot`` moments is ever recorded.

	``Command(name)`` types the theme's full name into the quicksearch, which
	matches with ``contains_chars``: a short name is a subsequence of a longer
	one ('Dark' also matches 'Gruvbox Dark'), and ties break by the sorted
	`names` order - which today always puts the exact name first. A future
	theme sorting *before* one whose name it contains ('Ayu Dark' before
	'Dark') would steal the query, so check the stills, not just how many
	were written.

	Length: ~7 s per theme (the name is typed a character at a time) against
	the tool's 300 s cap, i.e. ~40 themes. Its 60 s no-event watchdog is fed
	by the per-theme ``Screenshot``.
	"""
	steps = [
		Pause(1.0),
		# Pin the opacity before the first switch. The recording starts at
		# DEMO_OPACITY, but a theme may carry an `opacity` of its own, so
		# every switch below could move it. These stills are about color,
		# and a translucent window blends the desktop into the very colors
		# they are meant to show.
		PressKey('Ctrl+Shift+P'), Pause(0.6),
		Command('opacity'), Pause(1.2),
		Command('100'), Pause(1.2),
	]
	for name in names:
		steps += [
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('select theme'), Pause(1.2),
			Command(name), Pause(THEME_HOLD_S),
			Screenshot(name),
			# The tool saves a still from the next frame it *captures*, so
			# the palette has to stay closed for a moment afterwards.
			Pause(1.2),
		]
	return DemoScript(id=THEMES_DEMO_ID, name='themes', steps=tuple(steps))

def get_script(demo_id, theme_names):
	"""The DemoScript for `demo_id`, or None if there is no such demo."""
	if demo_id == THEMES_DEMO_ID:
		return build_themes_script(theme_names)
	return DEMOS.get(demo_id)

def demo_ids():
	return sorted(set(DEMOS) | {THEMES_DEMO_ID})
