"""Schedule quiet update checks after startup and once per running hour."""

FIRST_CHECK_DELAY_MS = 5 * 60 * 1000
TICK_INTERVAL_MS = 60 * 60 * 1000
UPDATE_COMMAND = 'check_for_updates'


class UpdateCheckTimer:
	def __init__(self, plugin_support, timer):
		self._plugin_support = plugin_support
		self._timer = timer

	def start(self):
		self._timer.timeout.connect(self._on_timeout)
		self._timer.start(FIRST_CHECK_DELAY_MS)

	def _on_timeout(self):
		self._timer.setInterval(TICK_INTERVAL_MS)
		if UPDATE_COMMAND in self._plugin_support.get_application_commands():
			self._plugin_support.run_application_command(
				UPDATE_COMMAND, {'silent': True}
			)
