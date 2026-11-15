"""Startup facts exposed for isolated automation checks."""

from dataclasses import dataclass


@dataclass
class StartupStatus:
	"""Record what startup did so automation can inspect its prompts."""

	window_shown: bool = False
	demo_mode: bool = False
	update_check_scheduled: bool = False
