from fman.impl.plugins import PluginSupport
from fman.impl.update_check import (
	FIRST_CHECK_DELAY_MS, TICK_INTERVAL_MS, UPDATE_COMMAND, UpdateCheckTimer,
)
from unittest import TestCase
from unittest.mock import MagicMock


class StubTimer:
	def __init__(self):
		self.timeout = MagicMock()
		self.start = MagicMock()
		self.setInterval = MagicMock()

	def fire(self):
		self.timeout.connect.call_args.args[0]()


class UpdateCheckTimerTest(TestCase):
	def setUp(self):
		self.plugin_support = MagicMock(spec=PluginSupport)
		self.plugin_support.get_application_commands.return_value = [UPDATE_COMMAND]
		self.timer = StubTimer()
		self.update_check = UpdateCheckTimer(self.plugin_support, self.timer)

	def test_start_delays_first_check(self):
		self.update_check.start()
		self.timer.start.assert_called_once_with(FIRST_CHECK_DELAY_MS)

	def test_fires_hourly_after_first_check(self):
		self.update_check.start()
		self.timer.fire()
		self.timer.setInterval.assert_called_once_with(TICK_INTERVAL_MS)
		self.timer.fire()
		self.assertEqual(
			2, self.plugin_support.run_application_command.call_count
		)
		self.plugin_support.run_application_command.assert_called_with(
			UPDATE_COMMAND, {'silent': True}
		)

	def test_missing_command_is_ignored(self):
		self.plugin_support.get_application_commands.return_value = []
		self.update_check.start()
		self.timer.fire()
		self.plugin_support.run_application_command.assert_not_called()
