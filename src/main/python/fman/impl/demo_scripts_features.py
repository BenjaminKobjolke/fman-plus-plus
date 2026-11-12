"""Standalone feature clips: one short recording per feature.

Split out of ``demo_scripts.py`` to keep both under the 300-line limit. See
``docs/DEMOS.md`` for how to record them and what each one is for.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, TypeText,
)

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
	21: DemoScript(
		id=21,
		name='feature-commands',
		steps=(
			Pause(1.5),
			# Every action below is run from the command palette, never by its
			# own key: the clip is about Ctrl+Shift+P reaching everyday work.
			# Each query equals the command's palette title, so it wins the
			# shortest-title sort ('delete' is Move to trash, not Delete
			# permanently). See "Palette queries" in docs/DEMOS.md.
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			TypeText('new folder'), Pause(1.2),
			PressKey('Return'), Pause(1.8),   # prompt selects its prefill late
			TypeText('archive'), Pause(1.0),
			PressKey('Return'), Pause(1.8),   # cursor lands on the new folder
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			TypeText('rename'), Pause(1.2),
			PressKey('Return'), Pause(1.6),   # inline editor, not a dialog
			PressKey('Ctrl+A'), Pause(0.3),
			TypeText('backup'), Pause(1.0),
			PressKey('Return'), Pause(1.8),
			# todo.txt sorts last, so End needs no Down count - and it is a
			# text file, so the viewer shows something readable.
			PressKey('End'), Pause(0.8),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			TypeText('view file'), Pause(1.2),
			PressKey('Return'), Pause(3.0),
			PressKey('Escape'), Pause(1.2),
			# Deletes the scratch copy of todo.txt only; the question defaults
			# to Yes, so Return confirms it.
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			TypeText('delete'), Pause(1.2),
			PressKey('Return'), Pause(1.8),
			PressKey('Return'), Pause(2.0),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			TypeText('select all'), Pause(1.2),
			PressKey('Return'), Pause(2.0),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			TypeText('deselect'), Pause(1.2),
			PressKey('Return'), Pause(2.0),
			# Nothing is selected any more, so Copy takes the file under the
			# cursor - independent of the deselect-after-transfer setting.
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			TypeText('copy'), Pause(1.2),
			PressKey('Return'), Pause(1.8),   # prompt: the other pane's path
			PressKey('Return'), Pause(2.5),
			Pause(1.0),
		),
	),
}
