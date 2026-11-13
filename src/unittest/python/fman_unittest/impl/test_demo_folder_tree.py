import importlib.util
import unittest


CONNECTOR_AVAILABLE = (
	importlib.util.find_spec('automated_screenshot_connector') is not None
)


class FolderTreeDemoTest(unittest.TestCase):
	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_demo_runs_commands_on_the_tree_folder_and_renames_it(self):
		from automated_screenshot_connector import PressKey, TypeText
		from fman.impl.demo_scripts_dialogs import DIALOG_CLIPS

		demo = DIALOG_CLIPS[22]
		self.assertEqual(demo.name, 'folder-tree')
		self.assertEqual(
			[
				step.name for step in demo.steps
				if step.__class__.__name__ == 'Screenshot'
			],
			[
				'folder-tree-expanded',
				'folder-tree-cursor-on-projects',
				'folder-tree-delete-confirm',
				'folder-tree-copy-prompt',
				'folder-tree-move-prompt',
				'folder-tree-rename-editing',
				'folder-tree-rename-cancelled',
				'folder-tree-renamed',
			],
		)
		self.assertEqual(
			[step.line for step in demo.steps if step.__class__.__name__ == 'Command'],
			['toggle folder tree', 'delete', 'copy', 'move'],
		)
		self.assertEqual(
			sum(
				isinstance(step, PressKey) and step.chord.casefold() == 'escape'
				for step in demo.steps
			),
			4,
		)
		return_steps = [
			(index, step) for index, step in enumerate(demo.steps)
			if isinstance(step, PressKey)
			and step.chord.casefold() in ('return', 'enter')
		]
		self.assertEqual(len(return_steps), 1)
		rename_editing_index = next(
			index for index, step in enumerate(demo.steps)
			if step.__class__.__name__ == 'Screenshot'
			and step.name == 'folder-tree-rename-editing'
		)
		self.assertGreater(return_steps[0][0], rename_editing_index)
		self.assertEqual(
			sum(
				isinstance(step, PressKey) and step.chord.casefold() == 'f2'
				for step in demo.steps
			),
			2,
		)
		self.assertEqual(
			sum(
				isinstance(step, TypeText) and step.text == 'clients'
				for step in demo.steps
			),
			1,
		)


if __name__ == '__main__':
	unittest.main()
