from core.commands.mixed_sorting import InitMixedSorting, ToggleMixedSorting
from unittest import TestCase
from unittest.mock import MagicMock, patch


class ToggleMixedSortingTest(TestCase):
	def test_toggle_on_persists_and_reloads_pane(self):
		pane = self._pane()
		settings = []
		with patch(
			'core.commands.hidden_files.load_json', return_value=settings
		), patch('core.commands.mixed_sorting.save_json') as save_json, patch(
			'core.commands.mixed_sorting.show_status_message'
		):
			ToggleMixedSorting(pane)()
		self.assertTrue(settings[0]['mix_files_and_folders'])
		pane._set_mix_dirs.assert_called_once_with(True)
		pane.reload.assert_called_once_with()
		save_json.assert_called_once_with('Panes.json')

	def test_toggle_off_persists_and_reloads_pane(self):
		pane = self._pane()
		settings = [{'mix_files_and_folders': True}]
		with patch(
			'core.commands.hidden_files.load_json', return_value=settings
		), patch('core.commands.mixed_sorting.save_json'), patch(
			'core.commands.mixed_sorting.show_status_message'
		):
			ToggleMixedSorting(pane)()
		self.assertFalse(settings[0]['mix_files_and_folders'])
		pane._set_mix_dirs.assert_called_once_with(False)
		pane.reload.assert_called_once_with()

	def test_pane_without_saved_value_defaults_to_off(self):
		pane = self._pane()
		settings = [{}]
		with patch(
			'core.commands.hidden_files.load_json', return_value=settings
		), patch('core.commands.mixed_sorting.save_json'), patch(
			'core.commands.mixed_sorting.show_status_message'
		):
			ToggleMixedSorting(pane)()
		self.assertTrue(settings[0]['mix_files_and_folders'])

	def _pane(self):
		pane = MagicMock()
		pane.window.get_panes.return_value = [pane]
		return pane


class InitMixedSortingTest(TestCase):
	def test_applies_saved_mixed_sorting(self):
		pane = MagicMock()
		pane.window.get_panes.return_value = [pane]
		with patch(
			'core.commands.hidden_files.load_json',
			return_value=[{'mix_files_and_folders': True}]
		):
			InitMixedSorting(pane)
		pane._set_mix_dirs.assert_called_once_with(True)

	def test_does_not_change_default_sorting(self):
		pane = MagicMock()
		pane.window.get_panes.return_value = [pane]
		with patch(
			'core.commands.hidden_files.load_json', return_value=[{}]
		):
			InitMixedSorting(pane)
		pane._set_mix_dirs.assert_not_called()
