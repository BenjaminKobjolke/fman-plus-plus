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

Demo 15 holds pane listing stills for the screenshot check. Add a still here
when a change affects how the file list looks. It hides and restores the pane
location bars, then hides them again and takes a still of a second fman started
on the same profile; run_fman_demo.bat starts it with them visible.

Demo 16 plays the fman account flow against the seeded DemoAccount fake; it
never reaches the real account or network.

Demo 17 needs the FTP plugin and fake server seeded by run_fman_demo.bat. It
checks that the progress window hides during a task question and returns after.

Demo 19 needs the locked file seeded by run_fman_demo.bat. It shows the single
retry question after a copy with a failed file, again after a failed retry, and
the file that did copy.

Demo 20 opens and closes the seeded video before the dialogs, because the
native video surface changes how in-window dialogs are shown (#15803).

Demo 22 holds a folder tree still with the current folder expanded, then takes
stills of Delete, Copy and Move from the palette with the tree cursor on
`projects` while the file list cursor stays on `archive`.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot, TypeText,
)
from fman.impl.demo import (
	ExpectChildWindow, LaunchFman, OpenContextMenu, ScreenStill,
	WaitForOverwriteQuestion,
)

# Keep this URL's port and account in sync with demo_ftp_server.py's
# PORT and authorizer.
DEMO_FTP_URL = 'ftp://demo:demo@127.0.0.1:21217/'

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
			PressKey('Shift+Delete'), Pause(1.5),
			Screenshot('dialog-delete-permanently-confirm'),
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
	16: DemoScript(
		id=16,
		name='fman-account',
		steps=(
			Pause(1.5),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('fman account'), Pause(1.0),
			Screenshot('fman-account-palette-signed-out'),
			PressKey('Escape'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('sign in to fman account'),
			Pause(2.0), Screenshot('fman-account-signed-in-alert'),
			PressKey('Return'), Pause(2.0),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('fman account'), Pause(1.0),
			Screenshot('fman-account-palette-signed-in'),
			PressKey('Escape'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('fman account'), Pause(2.0),
			Screenshot('fman-account-details'),
			PressKey('Escape'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('sign out of fman account'), Pause(1.5),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			TypeText('fman account'), Pause(1.0),
			Screenshot('fman-account-palette-after-sign-out'),
			PressKey('Escape'), Pause(1.0),
		),
	),
	17: DemoScript(
		id=17,
		name='ftp-overwrite',
		steps=(
			Pause(1.5),
			PressKey('Tab'),
			PressKey('Ctrl+Shift+P'),
			Pause(0.6),
			Command('open ftp location'),
			Pause(1.0),
			PressKey('Ctrl+A'),
			TypeText(DEMO_FTP_URL),
			PressKey('Return'),
			Pause(4.0),
			Screenshot('ftp-pane'),
			PressKey('Tab'),
			PressKey('F5'),
			Pause(1.5),
			PressKey('Return'),
			Pause(2.3),
			ScreenStill('ftp-progress-before-question'),
			WaitForOverwriteQuestion(),
			Pause(1.5),
			ScreenStill('ftp-progress-after-answer'),
			Pause(4.0),
		),
	),
	19: DemoScript(
		id=19,
		name='transfer-failure',
		steps=(
			Pause(2.5),
			PressKey('F5'), Pause(2.5), PressKey('Return'), Pause(6.0),
			ScreenStill('transfer-failure-retry-question'),
			PressKey('Return'), Pause(6.0),
			ScreenStill('transfer-failure-retry-again'),
			PressKey('Escape'), Pause(1.2),
			PressKey('Tab'), PressKey('Ctrl+R'), Pause(1.0),
			PressKey('Return'), Pause(1.5),
			Screenshot('transfer-failure-copied-rest'),
			Pause(1.0),
		),
	),
	20: DemoScript(
		id=20,
		name='dialogs-after-video',
		steps=(
			Pause(1.5),
			PressKey('Down'), Pause(0.2),
			PressKey('Down'), Pause(0.2),
			PressKey('Down'), Pause(0.2),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			Command('view file'), Pause(4.0),
			ScreenStill('after-video-playing'),
			PressKey('Escape'), Pause(1.5),
			ScreenStill('after-video-closed'),
			PressKey('Up'), Pause(0.2),
			PressKey('Up'), Pause(0.2),
			PressKey('Up'), Pause(0.2),
			PressKey('F8'), Pause(1.5),
			ScreenStill('after-video-delete-confirm'),
			PressKey('Escape'), Pause(1.2),
			ScreenStill('after-video-delete-cancelled'),
			PressKey('Ctrl+Shift+P'), Pause(1.0),
			ScreenStill('after-video-command-palette'),
			PressKey('Escape'), Pause(1.2),
			PressKey('F5'), Pause(1.8),
			ScreenStill('after-video-copy-prompt'),
			PressKey('Return'), Pause(2.0),
			PressKey('F5'), Pause(1.8), PressKey('Return'), Pause(2.0),
			ScreenStill('after-video-overwrite'),
			PressKey('Escape'), Pause(1.2), Pause(1.0),
		),
	),
	22: DemoScript(
		id=22,
		name='folder-tree',
		steps=(
			Pause(1.0),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('toggle folder tree'),
			Pause(4.0),
			Screenshot('folder-tree-expanded'),
			PressKey('Down'), Pause(0.3), PressKey('Down'), Pause(0.6),
			Screenshot('folder-tree-cursor-on-projects'),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('delete'), Pause(2.5),
			Screenshot('folder-tree-delete-confirm'),
			PressKey('Escape'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('copy'), Pause(1.8),
			Screenshot('folder-tree-copy-prompt'),
			PressKey('Escape'), Pause(1.2),
			PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('move'), Pause(1.8),
			Screenshot('folder-tree-move-prompt'),
			PressKey('Escape'), Pause(1.2),
			Pause(1.0),
		),
	),
}
