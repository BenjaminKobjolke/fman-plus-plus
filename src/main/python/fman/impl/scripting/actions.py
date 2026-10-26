"""Expose fman state and command dispatch to the scripting API."""

from fman.impl.single_instance import panes_active_first
from fman.impl.util.qt.thread import run_in_main_thread


class UnknownCommand(Exception):
	"""Raised when no pane or application command has the requested name."""


class InvalidPane(Exception):
	"""Raised when a command request selects a pane outside the current list."""


class ScriptingActions:
	def __init__(self, plugin_support, main_window):
		self._plugin_support = plugin_support
		self._main_window = main_window

	@run_in_main_thread
	def get_state(self):
		panes = panes_active_first(self._plugin_support, self._main_window)
		return {
			'active_pane': 0,
			'panes': [
				{
					'path': pane.get_path(),
					'cursor': pane.get_file_under_cursor(),
					'selection': pane.get_selected_files(),
				}
				for pane in panes
			],
		}

	def get_commands(self, config):
		panes = self._plugin_support.get_panes()
		pane_commands = set()
		for pane in panes:
			pane_commands.update(pane.get_commands())
		allowed = None if config.allow_all_commands else sorted(config.allowed_commands)
		return {
			'pane': sorted(pane_commands),
			'application': sorted(self._plugin_support.get_application_commands()),
			'allowed': allowed,
		}

	def run_command(self, name, args, pane_index):
		if name in self._plugin_support.get_application_commands():
			self._plugin_support.run_application_command(name, args)
		else:
			pane = self._get_pane(pane_index)
			if name in pane.get_commands():
				pane.run_command(name, args)
			else:
				raise UnknownCommand(name)

	@run_in_main_thread
	def _get_pane(self, pane_index):
		panes = panes_active_first(self._plugin_support, self._main_window)
		if pane_index is None:
			pane_index = 0
		if not isinstance(pane_index, int) or isinstance(pane_index, bool):
			raise InvalidPane('Pane index must be an integer.')
		if pane_index < 0:
			raise InvalidPane('Pane index is out of range.')
		try:
			return panes[pane_index]
		except IndexError:
			raise InvalidPane('Pane index is out of range.') from None
