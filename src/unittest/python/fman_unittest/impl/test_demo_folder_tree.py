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
	def test_demo_runs_commands_on_the_tree_folder_without_opening_a_folder(self):
		from automated_screenshot_connector import PressKey
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
			3,
		)
		self.assertFalse(
			any(
				isinstance(step, PressKey)
				and step.chord.casefold() in ('return', 'enter')
				for step in demo.steps
			)
		)


if __name__ == '__main__':
	unittest.main()
