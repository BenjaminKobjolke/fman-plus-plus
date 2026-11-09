import importlib.util
import json
import tomllib
import unittest
from pathlib import Path


CONNECTOR_AVAILABLE = (
	importlib.util.find_spec('automated_screenshot_connector') is not None
)


class DemoSetupTest(unittest.TestCase):
	def setUp(self):
		self.project_root = Path(__file__).resolve().parents[5]

	def test_demos_group_is_a_default_uv_group(self):
		with (self.project_root / 'pyproject.toml').open('rb') as pyproject_file:
			pyproject = tomllib.load(pyproject_file)

		self.assertIn('demos', pyproject['tool']['uv']['default-groups'])

	def test_release_freeze_excludes_the_connector(self):
		settings_path = self.project_root / 'src' / 'build' / 'settings' / 'base.json'
		with settings_path.open(encoding='utf-8') as settings_file:
			settings = json.load(settings_file)
		args = settings['extra_pyinstaller_args']
		self.assertIn(
			['--exclude-module', 'automated_screenshot_connector'],
			[
				args[index:index + 2]
				for index, arg in enumerate(args[:-1])
				if arg == '--exclude-module'
			],
		)

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_every_registered_demo_is_in_the_recorder_config(self):
		from fman.impl.demo_scripts import DEMOS, demo_ids

		config_path = self.project_root / 'tools' / 'create_media' / 'fman.json'
		with config_path.open(encoding='utf-8') as config_file:
			config = json.load(config_file)
		demos_by_id = {demo['id']: demo for demo in config['demos']}

		self.assertEqual(set(demo_ids()), set(demos_by_id))
		for demo_id, script in DEMOS.items():
			with self.subTest(demo_id=demo_id):
				self.assertEqual(demos_by_id[demo_id]['name'], script.name)

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_dialogs_demo_takes_a_still_of_each_dialog(self):
		from fman.impl.demo_scripts_dialogs import DIALOG_CLIPS

		demo = DIALOG_CLIPS[11]
		screenshot_names = [
			step.name for step in demo.steps
			if step.__class__.__name__ == 'Screenshot'
		]

		self.assertEqual(
			screenshot_names,
			[
				'dialog-copy-prompt',
				'dialog-overwrite',
				'dialog-delete-confirm',
				'dialog-copy-prompt-no-title-bar',
				'dialog-delete-confirm-no-title-bar',
			],
		)
		command_lines = [
			step.line for step in demo.steps
			if step.__class__.__name__ == 'Command'
		]
		self.assertEqual(
			command_lines,
			[
				'toggle title bar', 'copy', 'delete', 'toggle title bar',
			],
		)

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_links_demo_takes_a_still_of_each_link_screen(self):
		from fman.impl.demo_scripts_dialogs import DIALOG_CLIPS

		demo = DIALOG_CLIPS[12]
		screenshot_names = [
			step.name for step in demo.steps
			if step.__class__.__name__ == 'Screenshot'
		]

		self.assertEqual(demo.name, 'links')
		self.assertEqual(
			screenshot_names,
			['links-panes', 'link-target-palette', 'link-target-prompt'],
		)

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_context_menu_demo_takes_palette_and_menu_stills(self):
		from fman.impl.demo import OpenContextMenu
		from fman.impl.demo_scripts_dialogs import DIALOG_CLIPS

		demo = DIALOG_CLIPS[13]
		screenshot_names = [
			step.name for step in demo.steps
			if step.__class__.__name__ == 'Screenshot'
		]

		self.assertEqual(demo.name, 'context-menu')
		self.assertEqual(
			screenshot_names,
			['run-as-admin-palette', 'run-as-admin-context-menu'],
		)
		self.assertEqual(
			sum(isinstance(step, OpenContextMenu) for step in demo.steps),
			1,
		)

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_context_menu_demo_never_presses_return(self):
		from automated_screenshot_connector.steps import PressReturn, SendKey, flatten
		from fman.impl.demo_scripts_dialogs import DIALOG_CLIPS

		actions = [action for _, action in flatten(DIALOG_CLIPS[13].steps)]
		self.assertFalse(any(isinstance(action, PressReturn) for action in actions))
		self.assertFalse(
			any(
				isinstance(action, SendKey)
				and action.chord.casefold() in ('return', 'enter')
				for action in actions
			)
		)


if __name__ == '__main__':
	unittest.main()
