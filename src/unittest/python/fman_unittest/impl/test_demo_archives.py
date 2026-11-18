import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


CONNECTOR_AVAILABLE = (
	importlib.util.find_spec('automated_screenshot_connector') is not None
)


class DemoArchivesTest(unittest.TestCase):
	def setUp(self):
		self.project_root = Path(__file__).resolve().parents[5]

	def test_seed_creates_archive_folder_deep_archive_and_numbered_files(self):
		helper_path = (
			self.project_root / 'tools' / 'create_media' / 'seed_archive_demo.py'
		)
		spec = importlib.util.spec_from_file_location(
			'seed_archive_demo', helper_path,
		)
		helper = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(helper)

		with tempfile.TemporaryDirectory() as left_folder:
			with tempfile.TemporaryDirectory() as right_folder:
				left = Path(left_folder)
				right = Path(right_folder)
				(right / 'file2').write_text('stale fixture contents')
				helper.seed(left, right)

				self.assertTrue((left / 'old.zip').is_dir())
				with zipfile.ZipFile(left / 'old.zip' / 'inner.zip') as archive:
					self.assertEqual(archive.namelist(), ['inside-inner.txt'])
				with zipfile.ZipFile(right / 'deep.zip') as archive:
					self.assertEqual(
						archive.namelist(),
						['level1/level2/level3/level4/deep-file.txt'],
					)
					self.assertFalse(any(
						name.endswith('/') for name in archive.namelist()
					))
				for name in (
					'file2', 'file10', 'file999999', 'file1000000',
				):
					with self.subTest(name=name):
						self.assertTrue((right / name).is_file())
				self.assertEqual((right / 'file2').read_bytes(), b'')

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_archive_sorting_demo_takes_stills(self):
		from fman.impl.demo_scripts import DEMOS

		demo = DEMOS[30]
		still_names = [
			step.name for step in demo.steps
			if step.__class__.__name__ == 'Screenshot'
		]

		self.assertEqual(demo.name, 'archive-sorting')
		self.assertEqual(
			still_names,
			[
				'archive-sorting-panes',
				'archive-named-folder',
				'archive-inside-archive-named-folder',
				'archive-deep-root',
				'archive-deep-leaf',
			],
		)

	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_archive_sorting_demo_presses_return_only_on_folders_and_archives(self):
		from fman.impl.demo_scripts import DEMOS

		demo = DEMOS[30]
		return_steps = [
			step for step in demo.steps
			if step.__class__.__name__ == 'PressKey'
			and step.chord == 'Return'
		]

		self.assertEqual(len(return_steps), 7)


if __name__ == '__main__':
	unittest.main()
