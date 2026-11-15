"""Read startup prompt status from an isolated fman scripting session."""

import time
from typing import Any, Callable, Dict


POLL_INTERVAL_SECONDS = 0.1
STARTUP_TIMEOUT_SECONDS = 10


def read_startup_prompts(session: Dict[str, Any],
		api: Callable[[Dict[str, Any], str, str], Dict[str, Any]]) \
		-> Dict[str, Any]:
	"""Wait for the main window and return its startup state and dialog."""
	deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
	while time.monotonic() < deadline:
		state = api(session, 'GET', '/v1/state')
		startup = state.get('startup', {})
		if startup.get('window_shown'):
			dialog = api(session, 'GET', '/v1/dialog').get('dialog')
			return {
				'demo_mode': startup.get('demo_mode', False),
				'update_check_scheduled': startup.get(
					'update_check_scheduled', False),
				'dialog': dialog,
			}
		time.sleep(POLL_INTERVAL_SECONDS)
	raise RuntimeError('fman did not report its startup within 10 s.')
