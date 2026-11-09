"""Stills for the automated screenshot check of dialog changes.

Every dialog is cancelled and works only with demo 11's scratch data. The
cursor starts on the first file in the sorted left pane (changelog.txt); any
file is enough for F5 and F8.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot,
)

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
}
