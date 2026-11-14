"""Tests for the isolated fman UI driver's fixture setup."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import fixtures


class FixturesTest(TestCase):
	def test_make_fixture_creates_layout_and_controlled_age_files(self):
		now = 1_800_000_000
		with TemporaryDirectory() as temp, \
			patch.object(fixtures, '_hide') as hide:
			root = Path(temp) / 'fixture'
			fixtures.make_fixture(root, now)
			self.assertTrue((root / 'visible.txt').exists())
			self.assertTrue((root / 'hidden.txt').exists())
			self.assertTrue((root / 'folder').is_dir())
			self.assertTrue((root / '[--brackets--]' / 'visible.txt').exists())
			self.assertEqual(
				{item[0] for item in fixtures.AGE_FIXTURE_DAYS},
				{path.name for path in (root / fixtures.AGE_FOLDER).iterdir()},
			)
			for name, days, _ in fixtures.AGE_FIXTURE_DAYS:
				with self.subTest(name=name):
					self.assertAlmostEqual(
						now - days * fixtures.DAY_SECONDS,
						(root / fixtures.AGE_FOLDER / name).stat().st_mtime,
						delta=1,
					)
			hide.assert_any_call(root / 'hidden.txt')
			hide.assert_any_call(root / fixtures.AGE_FOLDER / 'age_10d_hidden.txt')

	def test_copy_video_fixture_copies_the_source(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			source = root / 'source.mp4'
			source.write_bytes(b'video fixture')
			destination = root / 'left'
			destination.mkdir()
			with patch.object(fixtures, 'VIDEO_SOURCE', Path('source.mp4')):
				fixtures.copy_video_fixture(destination, root)
			video = destination / fixtures.VIDEO_FIXTURE_NAME
			self.assertEqual(source.stat().st_size, video.stat().st_size)
			self.assertEqual(source.read_bytes(), video.read_bytes())

	def test_copy_video_fixture_reports_a_missing_source(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			source = root / 'missing.mp4'
			with patch.object(fixtures, 'VIDEO_SOURCE', Path('missing.mp4')):
				with self.assertRaises(FileNotFoundError) as error:
					fixtures.copy_video_fixture(root / 'left', root)
			self.assertIn(str(source), str(error.exception))

	def test_hide_sets_windows_hidden_attribute(self):
		with TemporaryDirectory() as temp:
			path = Path(temp) / 'hidden.txt'
			path.touch()
			with patch.object(fixtures.os, 'name', 'nt'), \
				patch.object(fixtures.subprocess, 'run') as run:
				fixtures._hide(path)
		run.assert_called_once_with(
			['attrib', '+h', str(path)], check=True,
			stdout=fixtures.subprocess.DEVNULL,
			stderr=fixtures.subprocess.DEVNULL,
		)

	def test_make_large_folder_creates_ordered_files_with_cycling_ages(self):
		now = 1_800_000_000
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'fixture'
			fixtures.make_large_folder(root, 3, now)
			files = sorted((root / fixtures.LARGE_FOLDER).iterdir())
			self.assertEqual(['file_00000.txt', 'file_00001.txt', 'file_00002.txt'],
				[path.name for path in files])
			for index, path in enumerate(files):
				self.assertAlmostEqual(
					now - (index % 400) * fixtures.DAY_SECONDS,
					path.stat().st_mtime, delta=1,
				)

	def test_make_large_folder_zero_does_not_create_directory(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'fixture'
			fixtures.make_large_folder(root, 0, 1_800_000_000)
		self.assertFalse((root / fixtures.LARGE_FOLDER).exists())

	def test_make_large_folder_rejects_invalid_counts(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'fixture'
			for count in (-1, fixtures.MAX_LARGE_COUNT + 1):
				with self.subTest(count=count), self.assertRaises(ValueError):
					fixtures.make_large_folder(root, count, 1_800_000_000)
		self.assertFalse(root.exists())

	def test_make_deep_folder_creates_siblings_at_each_level(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'fixture'
			deep = fixtures.make_deep_folder(root, 3)
			self.assertEqual(root / 'deep' / 'level_1' / 'level_2' /
				'level_3' / 'level_4' / 'level_5' / 'level_6', deep)
			for level in range(fixtures.DEEP_LEVELS):
				parent = root / 'deep'
				for index in range(1, level + 1):
					parent /= 'level_%d' % index
				self.assertEqual(
					['sibling_0000', 'sibling_0001', 'sibling_0002'],
					sorted(path.name for path in parent.iterdir()
						if path.name.startswith('sibling_')),
				)
			self.assertEqual([], list((deep).iterdir()))

	def test_make_deep_folder_zero_does_not_create_directory(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'fixture'
			self.assertIsNone(fixtures.make_deep_folder(root, 0))
		self.assertFalse(root.exists())

	def test_validate_deep_count_rejects_invalid_counts(self):
		for count in (-1, fixtures.MAX_DEEP_SIBLINGS + 1):
			with self.subTest(count=count), self.assertRaisesRegex(
				ValueError, r'--deep must be between 0 and 5000\.'):
				fixtures.validate_deep_count(count)

	def test_parse_core_settings_accepts_only_json_objects(self):
		self.assertIsNone(fixtures.parse_core_settings(None))
		self.assertEqual({'file_age_style': 'tint'},
			fixtures.parse_core_settings('{"file_age_style":"tint"}'))
		for text in ('[1]', 'null', '"text"'):
			with self.subTest(text=text), self.assertRaisesRegex(
				ValueError, '--core-settings must be a JSON object.'):
				fixtures.parse_core_settings(text)

	def test_write_core_settings_writes_parsed_object_or_nothing(self):
		with TemporaryDirectory() as temp:
			profile = Path(temp) / 'profile'
			fixtures.write_core_settings(profile, None)
			settings_path = profile.joinpath(*fixtures.CORE_SETTINGS_PATH)
			self.assertFalse(settings_path.exists())
			fixtures.write_core_settings(
				profile, fixtures.parse_core_settings('{"file_age_scale":"steps"}'))
			self.assertEqual({'file_age_scale': 'steps'},
				json.loads(settings_path.read_text(encoding='utf-8')))

