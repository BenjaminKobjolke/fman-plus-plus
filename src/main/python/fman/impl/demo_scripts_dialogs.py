"""Stills for the automated screenshot check of dialog changes.

Every dialog is cancelled and works only with demo 11's scratch data. The
cursor starts on the first file in the sorted left pane (changelog.txt); any
file is enough for F5 and F8.

Demo 13 never presses Return, because that would run the file elevated.

Demo 12 needs the junction and shortcut seeded by run_fman_demo.bat; its
cursor starts on the junction because directories sort first, and the prompt
is cancelled.

Demo 14 holds one palette search still per palette command that a screenshot
check needs.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot, TypeText,
)
from fman.impl.demo import OpenContextMenu

DIALOG_CLIPS = {
	11: DemoScript(
		id=11,
		name='dialogs',
		steps=(
			Pause(1.5),
			PressKey('F5'), Pause(1.8), Screenshot('dialog-copy-prompt'),
			PressKey('Return'), Pause(2.0),
			PressKey('F5'), Pause(1.8), PressKey('Return'), Pause(2.0),
			Screenshot('dialog-overwrite'),
			PressKey('Escape'), Pause(1.2),
			PressKey('F8'), Pause(1.5), Screenshot('dialog-delete-confirm'),
			PressKey('Escape'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle title bar'), Pause(1.5),
			# Recreating the native window loses pane focus. Use the palette's
			# commands so the frameless dialogs still open deterministically.
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('copy'), Pause(1.8),
			Screenshot('dialog-copy-prompt-no-title-bar'),
			PressKey('Escape'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('delete'), Pause(1.5),
			Screenshot('dialog-delete-confirm-no-title-bar'),
			PressKey('Escape'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle title bar'), Pause(1.5),
			Pause(1.0),
		),
	),
	12: DemoScript(
		id=12,
		name='links',
		steps=(
			Pause(1.5),
			Screenshot('links-panes'),
			PressKey('Ctrl+Shift+P'),
			Pause(0.6),
			TypeText('edit link target'),
			Pause(1.0),
			Screenshot('link-target-palette'),
			PressKey('Return'),
			Pause(1.8),
			Screenshot('link-target-prompt'),
			PressKey('Escape'),
			Pause(1.2),
			Pause(1.0),
		),
	),
	13: DemoScript(
		id=13,
		name='context-menu',
		steps=(
			Pause(1.5),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('run as administrator'), Pause(1.0),
			Screenshot('run-as-admin-palette'),
			PressKey('Escape'), Pause(1.2),
			OpenContextMenu(), Pause(1.5),
			Screenshot('run-as-admin-context-menu'),
			PressKey('Escape'), Pause(1.2),
			Pause(1.0),
		),
	),
	14: DemoScript(
		id=14,
		name='command-palette',
		steps=(
			Pause(1.5), PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('go to network'), Pause(1.0),
			Screenshot('go-to-network-palette'),
			PressKey('Return'), Pause(20.0),
			Screenshot('go-to-network-pane'), Pause(1.0),
		),
	),
}
