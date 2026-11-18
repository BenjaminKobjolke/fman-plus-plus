"""Run the installer and persist its eventual exit code for the driver."""

import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

from installer_session import setup_command, setup_environment


def run(session_dir, setup, install_dir):
	session_dir = Path(session_dir)
	result_path = session_dir / 'installer_exit.json'
	try:
		result = subprocess.run(
			setup_command(setup, install_dir),
			env=setup_environment(), timeout=600, check=False)
		data = {'exit_code': result.returncode}
	except subprocess.TimeoutExpired:
		data = {'exit_code': None, 'error': 'timeout'}
	data['ended_at'] = datetime.now(timezone.utc).timestamp()
	result_path.write_text(json.dumps(data), encoding='utf-8')
	return data


def main(argv=None):
	argv = sys.argv[1:] if argv is None else argv
	if len(argv) != 3:
		raise SystemExit('usage: installer_waiter <session_dir> <setup> <install_dir>')
	run(*argv)
	return 0


if __name__ == '__main__':
	sys.exit(main())
