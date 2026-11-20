import importlib.util
import tempfile
import unittest
from pathlib import Path


CONNECTOR_AVAILABLE = (
	importlib.util.find_spec('automated_screenshot_connector') is not None
)


class DemoCopyProgressTest(unittest.TestCase):
	def setUp(self):
		self.project_root = Path(__file__).resolve().parents[5]

	def test_seed_creates_copy_progress_files_and_is_idempotent(self):
		helper_path = (
			self.project_root / 'tools' / 'create_media'
			/ 'seed_copy_progress_demo.py'
		)
		spec = importlib.util.spec_from_file_location(
			'seed_copy_progress_demo', helper_path,
		)
		helper = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(helper)
		helper.FILE_COUNT = 5

		with tempfile.TemporaryDirectory() as left_folder:
			left = Path(left_folder)
			helper.seed(left)
			helper.seed(left)

			files = sorted((left / 'copy-progress').iterdir())
			self.assertEqual(
				[file.name for file in files],
				[f'file_{index:05d}.bin' for index in range(5)],
			)
			self.assertTrue(all(
				file.is_file() and file.stat().st_size == helper.FILE_SIZE
				for file in files
			))

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_demo_records_window_and_screen_progress_stills(self):
		from fman.impl.demo_scripts import DEMOS

		demo = DEMOS[33]
		screenshot_index = next(
			index for index, step in enumerate(demo.steps)
			if step.__class__.__name__ == 'Screenshot'
			and step.name == 'copy-progress-window'
		)
		return_index = next(
			index for index, step in enumerate(demo.steps)
			if step.__class__.__name__ == 'PressKey'
			and step.chord == 'Return'
		)
		screen_stills = [
			step.name for step in demo.steps
			if step.__class__.__name__ == 'ScreenStill'
		]

		self.assertEqual(demo.name, 'copy-progress')
		self.assertGreater(screenshot_index, return_index)
		self.assertIn('copy-progress-screen', screen_stills)
		self.assertIn('copy-progress-canceled', screen_stills)


if __name__ == '__main__':
	unittest.main()
