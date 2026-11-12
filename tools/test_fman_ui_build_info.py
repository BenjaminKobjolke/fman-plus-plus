"""Tests for build details reported by the fman UI automation driver."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import build_info


class BuildInfoTest(TestCase):
	def test_describe_build_reads_version_and_git_details(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			settings = root / 'src' / 'build' / 'settings' / 'base.json'
			settings.parent.mkdir(parents=True)
			settings.write_text(json.dumps({'version': '1.2.3'}), encoding='utf-8')
			with patch.object(build_info.subprocess, 'run', side_effect=(
				SimpleNamespace(returncode=0, stdout='abc123\n'),
				SimpleNamespace(returncode=0, stdout=' M tracked.py\n'),
			)) as run:
				result = build_info.describe_build(root, 'python.exe')

		self.assertEqual('1.2.3', result.version)
		self.assertEqual('abc123', result.commit)
		self.assertTrue(result.dirty)
		self.assertEqual(str(root.resolve()), result.checkout_path)
		self.assertEqual('python.exe', result.python)
		self.assertEqual(2, run.call_count)
		self.assertTrue(all(call.kwargs['cwd'] == root.resolve()
			for call in run.call_args_list))

	def test_describe_build_uses_none_when_version_and_git_are_unavailable(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			with patch.object(build_info.subprocess, 'run', return_value=
				SimpleNamespace(returncode=128, stdout='')):
				result = build_info.describe_build(root, 'python.exe')

		self.assertIsNone(result.version)
		self.assertIsNone(result.commit)
		self.assertIsNone(result.dirty)

