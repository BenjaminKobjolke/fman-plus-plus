"""Command line parser for the fman UI automation driver."""

import argparse

from window_size import MIN_HEIGHT, MIN_WIDTH


def parser():
	parser = argparse.ArgumentParser(prog='fman_ui')
	commands = parser.add_subparsers(dest='action', required=True)
	launch = commands.add_parser('launch')
	launch.add_argument('--left')
	launch.add_argument('--right')
	launch.add_argument('--large', type=int, default=0,
		help="number of files in the left fixture's large folder")
	launch.add_argument('--deep', type=int, default=0,
		help=("number of sibling folders per level in the left fixture's "
			"deep folder tree"))
	launch.add_argument('--network-share', action='store_true',
		help=("create a share folder reachable as "
			"\\\\localhost\\<drive>$ for network checks"))
	launch.add_argument('--core-settings', default=None,
		help=("JSON object written to the profile's Core Settings.json "
			"before fman starts"))
	launch.add_argument('--previous-version',
		help=("saved fman version written to the profile so startup "
			"shows the update message"))
	launch.add_argument('--first-start', action='store_true',
		help="start with no saved fman settings or session")
	launch.add_argument('--demo', type=int, metavar='ID',
		help=("start fman in automation demo mode with this demo id; "
			"consent stays unanswered"))
	for name in ('state', 'commands', 'close', 'dialog', 'restart', 'links',
			'native-windows', 'close-native-windows'):
		commands.add_parser(name)
	viewer = commands.add_parser('viewer')
	viewer.add_argument('--pane', type=int, default=0)
	command = commands.add_parser('command')
	command.add_argument('name')
	command.add_argument('args_json', nargs='?', default='{}')
	command.add_argument('--pane', type=int, default=0)
	command.add_argument('--settle', type=int, default=500)
	files = commands.add_parser('files')
	files.add_argument('--pane', type=int, default=0)
	keys = commands.add_parser('keys')
	keys.add_argument('chords', nargs='+')
	keys.add_argument('--settle', type=int, default=500)
	type_text = commands.add_parser('type')
	type_text.add_argument('text')
	type_text.add_argument('--settle', type=int, default=500)
	click = commands.add_parser('click')
	choice = click.add_mutually_exclusive_group(required=True)
	choice.add_argument('--file')
	choice.add_argument('--x', type=int)
	click.add_argument('--y', type=int)
	click.add_argument('--pane', type=int, default=0)
	click.add_argument('--right', action='store_true')
	click.add_argument('--double', action='store_true')
	click.add_argument('--settle', type=int, default=500)
	drag = commands.add_parser('drag')
	drag.add_argument('--x', type=int, required=True)
	drag.add_argument('--y', type=int, required=True)
	drag.add_argument('--to-x', type=int, required=True)
	drag.add_argument('--to-y', type=int, required=True)
	drag.add_argument('--settle', type=int, default=500)
	hover = commands.add_parser('hover')
	hover.add_argument('--x', type=int, required=True)
	hover.add_argument('--y', type=int, required=True)
	hover.add_argument('--settle', type=int, default=500)
	window = commands.add_parser('window')
	window.add_argument('--width', type=int, default=MIN_WIDTH)
	window.add_argument('--height', type=int, default=MIN_HEIGHT)
	window.add_argument('--x', type=int)
	window.add_argument('--y', type=int)
	window.add_argument('--screen', type=int)
	screenshot = commands.add_parser('screenshot')
	screenshot.add_argument('png_path')
	screenshot.add_argument('--screen', action='store_true')
	return parser
