"""Stills for screenshot checks of packing changes, including network paths.

The launcher seeds the right pane with a ``network://`` URL so these stills
exercise archive creation through the same filesystem path as network shares.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot, TypeText,
)


PACK_CLIPS = {
	27: DemoScript(
		id=27,
		name='pack',
		steps=(
			Pause(1.5),
			Screenshot('pack-panes'),
			PressKey('Down'), PressKey('Down'), PressKey('Down'), PressKey('Down'),
			PressKey('Alt+F5'), Pause(1.8), Screenshot('pack-prompt'),
			PressKey('Return'), Pause(3.5),
			PressKey('Tab'), PressKey('Ctrl+R'), Pause(1.5),
			Screenshot('pack-network-result'),
			PressKey('Tab'), Pause(0.6),
			PressKey('Down'), PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('pack pass'), Pause(1.8),
			Screenshot('pack-password-prompt'),
			PressKey('Return'), Pause(1.6), TypeText('demo'), PressKey('Return'),
			Pause(1.6), TypeText('demo'), PressKey('Return'), Pause(3.5),
			PressKey('Tab'), PressKey('Ctrl+R'), Pause(1.5),
			Screenshot('pack-password-result'),
			PressKey('Tab'), Pause(0.6),
			PressKey('Down'), PressKey('Ctrl+Shift+P'), Pause(0.6),
			Command('pack here'), Pause(1.8), PressKey('Return'), Pause(3.0),
			PressKey('Ctrl+R'), Pause(1.5), Screenshot('pack-here-result'),
			PressKey('Alt+F5'), Pause(1.8), PressKey('Ctrl+A'), Pause(0.5),
			TypeText('missing-folder\\archive.zip'), PressKey('Return'), Pause(1.5),
			Screenshot('pack-missing-folder-alert'),
			PressKey('Return'), Pause(1.0),
		),
	),
}
