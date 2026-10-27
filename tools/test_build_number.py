"""Tests for plain semantic release version handling."""

import unittest
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "release"))
import build_number


class NextVersionTest(unittest.TestCase):
    def test_patch_rollover(self):
        self.assertEqual(build_number.next_version("1.7.13"), "1.8.0")

    def test_increments_patch(self):
        self.assertEqual(build_number.next_version("1.8.0"), "1.8.1")

    def test_patch_maximum_is_included(self):
        self.assertEqual(build_number.next_version("1.8.9"), "1.8.10")

    def test_patch_maximum_rolls_over(self):
        self.assertEqual(build_number.next_version("1.8.10"), "1.9.0")


class SettingsFileTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="build-number-")
        self.addCleanup(self.temporary.cleanup)
        self.settings_file = Path(self.temporary.name) / "base.json"
        self.settings_patcher = patch.object(
            build_number, "_SETTINGS_FILE", self.settings_file
        )
        self.settings_patcher.start()
        self.addCleanup(self.settings_patcher.stop)
        self.tags_patcher = patch.object(build_number, "_git_tags", return_value=[])
        self.tags_patcher.start()
        self.addCleanup(self.tags_patcher.stop)

    def write_settings(self, contents):
        self.settings_file.write_text(contents, encoding="utf-8")


class IncrementTest(SettingsFileTestCase):
    def test_updates_only_version_and_preserves_formatting(self):
        original = (
            '{\n'
            '  "other": [1, 2],\n'
            '  "version": "1.8.9",\n'
            '  "nested": {"enabled": true}\n'
            '}\n'
        )
        expected = original.replace('"version": "1.8.9"', '"version": "1.8.10"')
        self.write_settings(original)
        self.assertEqual(build_number.increment(), "1.8.10")
        self.assertEqual(self.settings_file.read_text(encoding="utf-8"), expected)


class ReleasedVersionTest(unittest.TestCase):
    def test_ignores_non_plain_release_tags_and_uses_numeric_order(self):
        tags = ["1.7.13_8", "1.8.9", "1.8.10", "v2", "notes"]
        with patch.object(build_number, "_git_tags", return_value=tags):
            self.assertEqual(build_number.released_version(), "1.8.10")

    def test_returns_none_without_plain_release_tags(self):
        with patch.object(build_number, "_git_tags", return_value=[]):
            self.assertIsNone(build_number.released_version())


class VersionFloorTest(SettingsFileTestCase):
    def test_lost_bump_uses_newest_tag_for_label_and_increment(self):
        self.write_settings('{"version": "1.8.1"}\n')
        with patch.object(build_number, "_git_tags", return_value=["1.8.1", "1.8.2"]):
            self.assertEqual(build_number.label(), "1.8.2")
            self.assertEqual(build_number.increment(), "1.8.3")
        self.assertEqual(build_number._settings_version(), "1.8.3")

    def test_settings_version_ahead_of_tags_wins(self):
        self.write_settings('{"version": "1.8.3"}\n')
        with patch.object(build_number, "_git_tags", return_value=["1.8.2"]):
            self.assertEqual(build_number.label(), "1.8.3")


if __name__ == "__main__":
    unittest.main()
