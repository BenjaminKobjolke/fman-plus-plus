"""Command line parser for the fman UI automation driver."""

import argparse


def parser():
	parser = argparse.ArgumentParser(prog='fman_ui')
	commands = parser.add_subparsers(dest='action', required=True)
	launch = commands.add_parser('launch')
	launch.add_argument('--left')
	launch.add_argument('--right')
	launch.add_argument('--large', type=int, default=0,
		help="number of files in the left fixture's large folder")
	launch.add_argument('--core-settings', default=None,
		help=("JSON object written to the profile's Core Settings.json "
			"before fman starts"))
	for name in ('state', 'commands', 'close', 'dialog', 'restart'):
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
	screenshot = commands.add_parser('screenshot')
	screenshot.add_argument('png_path')
	return parser
