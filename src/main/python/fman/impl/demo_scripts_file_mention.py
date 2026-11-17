"""Stills for the @ file search exclusion commands.

The script needs the ``build`` folder seeded by ``run_fman_demo.bat``. It is
the first row because directories sort first, so the cursor starts on it. The
@ file mention popup is reached through Go To followed by ``@``.
"""

from automated_screenshot_connector import (
	Command, DemoScript, Pause, PressKey, Screenshot, TypeText,
)


FILE_MENTION_CLIPS = {
	28: DemoScript(
		id=28,
		name='file-mention-exclusions',
		steps=(
			Pause(1.5),
			PressKey('Ctrl+P'), Pause(0.8), TypeText('@output'), Pause(1.5),
			Screenshot('file-mention-before'), PressKey('Escape'), Pause(1.0),
			PressKey('Ctrl+Shift+P'), Pause(0.6), Command('exclude folder'),
			Pause(1.8), Screenshot('file-mention-exclude-prompt'),
			PressKey('Return'), Pause(1.2),
			PressKey('Ctrl+P'), Pause(0.8), TypeText('@output'), Pause(1.5),
			Screenshot('file-mention-excluded'), PressKey('Escape'), Pause(1.0),
			PressKey('Ctrl+Shift+P'), Pause(0.6), Command('remove folder from'),
			Pause(1.5), TypeText('build'), Pause(1.0),
			Screenshot('file-mention-remove-quicksearch'),
			PressKey('Return'), Pause(1.2),
			PressKey('Ctrl+P'), Pause(0.8), TypeText('@output'), Pause(1.5),
			Screenshot('file-mention-included-again'),
			PressKey('Escape'), Pause(1.0),
		),
	),
}
