from unittest import TestCase
from unittest.mock import Mock, patch

from core.selection_summary import SelectionStats, SelectionSummaryLocation
from core.commands import (
	SelectionSummaryListener,
	ToggleSelectionFolderSizes,
	ToggleSelectionSummaryLocation,
)
from core.commands.selection_summary import SelectionSummaryListener as Listener


class SelectionSummaryListenerTest(TestCase):
	def setUp(self):
		self.pane = Mock()
		self.pane.get_selected_files.return_value = []
		with (
			patch(
				'core.commands.selection_summary.measure',
				return_value=SelectionStats(0, 0, None),
			),
			patch(
				'core.commands.selection_summary.get_folder_sizes_enabled',
				return_value=False,
			),
		):
			self.listener = Listener(self.pane)
		self.pane.set_idle_status_message.reset_mock()

	def test_registered_listener_uses_placement_flags(self):
		self.assertIs(SelectionSummaryListener, Listener)
		with patch(
			'core.commands.selection_summary.get_summary_location',
			return_value=SelectionSummaryLocation.BOTH,
		):
			self.listener._show_summary('2 files selected')
		self.pane.set_idle_status_message.assert_called_once_with(
			'2 files selected', pane_line=True, status_bar=True,
		)

	def test_old_generation_cannot_replace_a_newer_summary(self):
		self.listener._generation = 2
		self.listener._apply_measurement(
			1, SelectionStats(1, 0, 10),
		)
		self.pane.set_idle_status_message.assert_not_called()

	def test_current_generation_updates_the_idle_summary(self):
		self.listener._generation = 2
		with patch(
			'core.commands.selection_summary.format_summary',
			return_value='1 file selected, 10 B',
		):
			self.listener._apply_measurement(
				2, SelectionStats(1, 0, 10),
			)
		self.pane.set_idle_status_message.assert_called_once()


class SelectionSummaryCommandsTest(TestCase):
	def test_location_command_cycles_setting_and_reports_new_location(self):
		self.assertIs(
			ToggleSelectionSummaryLocation,
			__import__('core.commands.selection_summary', fromlist=[
				'ToggleSelectionSummaryLocation'
			]).ToggleSelectionSummaryLocation,
		)
		with (
			patch(
				'core.commands.selection_summary.get_summary_location',
				return_value=SelectionSummaryLocation.PANE,
			),
			patch('core.commands.selection_summary.save_setting') as save_setting,
			patch('core.commands.selection_summary.show_status_message') as show_status,
			patch('core.commands.selection_summary._refresh_panes') as refresh,
		):
			ToggleSelectionSummaryLocation(Mock())()
		save_setting.assert_called_once_with(
			'Core Settings.json', 'selection_summary_location', 'window',
		)
		show_status.assert_called_once_with(
			'Selection summary location: window', timeout_secs=3,
		)
		refresh.assert_called_once()

	def test_folder_size_command_toggles_setting_and_reports_state(self):
		with (
			patch(
				'core.commands.selection_summary.get_folder_sizes_enabled',
				return_value=False,
			),
			patch('core.commands.selection_summary.save_setting') as save_setting,
			patch('core.commands.selection_summary.show_status_message') as show_status,
			patch('core.commands.selection_summary._refresh_panes') as refresh,
		):
			ToggleSelectionFolderSizes(Mock())()
		save_setting.assert_called_once_with(
			'Core Settings.json', 'selection_summary_folder_sizes', True,
		)
		show_status.assert_called_once_with(
			'Selection folder sizes: on', timeout_secs=3,
		)
		refresh.assert_called_once()
