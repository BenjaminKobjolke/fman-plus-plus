"""Call fman's scripting API from Python (standard library only).

Usage:
    python fman_api.py state
    python fman_api.py commands
    python fman_api.py command <name> [args-json] [--pane N]

Examples:
    python fman_api.py command move_cursor_down
    python fman_api.py command open_directory "{\"url\": \"file://C:/Windows\"}"
    python fman_api.py command reload --pane 1

The cmd quoting above differs in PowerShell 7: '{"url": "file://C:/Windows"}'.

Set FMAN_API_URL to override the default http://127.0.0.1:47447.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = os.environ.get('FMAN_API_URL', 'http://127.0.0.1:47447')
TOKEN_FILE = Path(os.environ['APPDATA']) / 'fman' / 'Local' / 'ScriptingApiToken.txt'


def call(path, body=None):
	token = TOKEN_FILE.read_text(encoding='utf-8').strip()
	headers = {'Authorization': f'Bearer {token}'}
	data = None
	if body is not None:
		data = json.dumps(body).encode('utf-8')
		headers['Content-Type'] = 'application/json'
	request = Request(API_URL + path, data=data, headers=headers)
	with urlopen(request) as response:
		return json.load(response)


def main():
	parser = argparse.ArgumentParser(description='fman scripting API client')
	sub = parser.add_subparsers(dest='action', required=True)
	sub.add_parser('state', help='print the panes, cursor and selection')
	sub.add_parser('commands', help='list available and allowed commands')
	cmd = sub.add_parser('command', help='run a command')
	cmd.add_argument('name')
	cmd.add_argument('args', nargs='?', default='{}', help='JSON object')
	cmd.add_argument('--pane', type=int, help='pane index, 0 = active')
	options = parser.parse_args()

	try:
		if options.action == 'state':
			result = call('/v1/state')
		elif options.action == 'commands':
			result = call('/v1/commands')
		else:
			body = {'name': options.name, 'args': json.loads(options.args)}
			if options.pane is not None:
				body['pane'] = options.pane
			result = call('/v1/command', body)
	except json.JSONDecodeError as error:
		sys.exit(f'args is not a JSON object: {error}')
	except FileNotFoundError:
		sys.exit(
			f'No token file at {TOKEN_FILE}. '
			'Run "Toggle scripting API" in fman first.')
	except HTTPError as error:
		sys.exit(f'HTTP {error.code}: {error.read().decode("utf-8")}')
	except URLError as error:
		sys.exit(f'Cannot reach fman at {API_URL}: {error.reason}')
	print(json.dumps(result, indent=2))


if __name__ == '__main__':
	main()
