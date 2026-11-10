from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import Mock, patch

import fman
from fman.impl.widgets import DirectoryPaneWidget

from core.file_age import (
	FileAgeOptions, age_amount, load_options, make_age_shader,
)
from core.commands import ToggleFileAgeShading
from core.commands.file_age_shading import (
	InitFileAgeShading as InitListener,
	ToggleFileAgeShading as ToggleCommand,
)


class ApplyTest(TestCase):
	def test_disabled_shading_clears_through_public_pane_api(self):
		widget = Mock(spec=DirectoryPaneWidget)
		pane = fman.DirectoryPane(None, widget, None)
		with patch('core.file_age.get_setting', return_value=False):
			from core.file_age import apply
			apply(pane)
		widget.set_file_shading.assert_called_once_with(None, 'transparency')
	def test_enabled_shading_passes_shader_and_configured_style(self):
		widget = Mock(spec=DirectoryPaneWidget)
		pane = fman.DirectoryPane(None, widget, None)
		with patch(
				'core.file_age.get_setting',
				side_effect=[True, 'log', 'bold', 365]
		):
			from core.file_age import apply
			apply(pane)
		args, _kwargs = widget.set_file_shading.call_args
		self.assertTrue(callable(args[0]))
		self.assertEqual('bold', args[1])


class AgeAmountTest(TestCase):
	def test_log_scale_has_expected_boundaries_and_is_monotonic(self):
		self.assertEqual(0, age_amount(0, 'log', 365))
		self.assertEqual(1, age_amount(365, 'log', 365))
		amounts = [age_amount(days, 'log', 365) for days in range(366)]
		self.assertEqual(sorted(amounts), amounts)
		self.assertEqual(1, age_amount(1000, 'log', 365))
	def test_steps_use_day_week_month_boundaries(self):
		self.assertEqual(0, age_amount(.99, 'steps', 365))
		self.assertEqual(1 / 3, age_amount(1, 'steps', 365))
		self.assertEqual(1 / 3, age_amount(6.99, 'steps', 365))
		self.assertEqual(2 / 3, age_amount(7, 'steps', 365))
		self.assertEqual(2 / 3, age_amount(29.99, 'steps', 365))
		self.assertEqual(1, age_amount(30, 'steps', 365))
	def test_negative_age_is_clamped_to_zero(self):
		self.assertEqual(0, age_amount(-2, 'log', 365))


class FileAgeOptionsTest(TestCase):
	def test_defaults_and_invalid_values_fall_back(self):
		with patch('core.file_age.get_setting', return_value=None):
			self.assertEqual(
				FileAgeOptions(False, 'log', 'transparency', 365),
				load_options()
			)
		with patch(
				'core.file_age.get_setting',
				side_effect=[1, 'invalid', 'bad', -5]
		):
			self.assertEqual(
				FileAgeOptions(False, 'log', 'transparency', 365),
				load_options()
			)
		with patch(
				'core.file_age.get_setting',
				side_effect=[True, 'log', 'transparency', float('inf')]
		):
			self.assertEqual(
				FileAgeOptions(True, 'log', 'transparency', 365),
				load_options()
			)
	def test_valid_values_are_loaded(self):
		with patch(
				'core.file_age.get_setting',
				side_effect=[True, 'steps', 'bold', 30]
		):
			self.assertEqual(
				FileAgeOptions(True, 'steps', 'bold', 30), load_options()
			)


class MakeAgeShaderTest(TestCase):
	def test_skips_non_local_urls_and_missing_or_raising_dates(self):
		shader = make_age_shader(FileAgeOptions(True, 'log', 'transparency', 365))
		with patch('core.file_age.modified_datetime') as modified:
			self.assertIsNone(shader('sftp://host/file'))
			modified.assert_not_called()
			modified.return_value = None
			self.assertIsNone(shader('file:///missing'))
			modified.side_effect = OSError('gone')
			self.assertIsNone(shader('file:///gone'))
	def test_future_dates_are_fresh_and_bold_changes_at_one_day(self):
		options = FileAgeOptions(True, 'log', 'bold', 365)
		shader = make_age_shader(options)
		now = datetime(2026, 1, 2, 12)
		with patch('core.file_age.modified_datetime') as modified, \
				patch('core.file_age.datetime') as clock:
			clock.now.return_value = now
			modified.return_value = now + timedelta(days=1)
			self.assertEqual(0, shader('file:///future'))
			modified.return_value = now - timedelta(hours=23, minutes=59)
			self.assertEqual(0, shader('file:///new'))
			modified.return_value = now - timedelta(days=1)
			self.assertEqual(1, shader('file:///old'))


class FileAgeShadingCommandTest(TestCase):
	def test_toggle_is_registered_and_applies_to_every_pane(self):
		self.assertIs(ToggleFileAgeShading, ToggleCommand)
		self.assertEqual(('Toggle file age shading',), ToggleCommand.aliases)
		panes = [object(), object()]
		window = type('Window', (), {'get_panes': lambda _self: panes})()
		command = ToggleCommand(window)
		with patch(
				'core.commands.file_age_shading.is_enabled',
				side_effect=(True, False)
		), \
				patch('core.commands.file_age_shading.save_setting') as save_setting, \
				patch('core.commands.file_age_shading.apply') as apply, \
				patch('core.commands.file_age_shading.show_status_message') as status:
			command()
			command()
		save_setting.assert_has_calls([
			(('Core Settings.json', 'file_age_shading', False),),
			(('Core Settings.json', 'file_age_shading', True),),
		])
		self.assertEqual(4, apply.call_count)
		apply.assert_any_call(panes[0])
		apply.assert_any_call(panes[1])
		status.assert_has_calls([
			(('File age shading: off',), {'timeout_secs': 3}),
			(('File age shading: on',), {'timeout_secs': 3}),
		])
	def test_listener_applies_on_initialization_and_path_changes(self):
		pane = object()
		with patch('core.commands.file_age_shading.apply') as apply:
			listener = InitListener(pane)
			listener.on_path_changed()
		self.assertEqual(2, apply.call_count)
		apply.assert_called_with(pane)
