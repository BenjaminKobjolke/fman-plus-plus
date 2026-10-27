"""Shared fixtures for native Robocopy integration tests."""

import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase

from fman.url import as_url

from robocopy_plugin import planner, settings, windows


class RobocopyFixture(TestCase):
	def setUp(self):
		self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
		self.source, self.destination = self.root / 'source', self.root / 'destination'
		self.source.mkdir()
		self.executable = windows.executable()
	def plan(self, names, move=False, options=None, log=None):
		return planner.prepare(as_url(self.source),
			tuple(as_url(self.source / name) for name in names), str(self.destination),
			self.executable, options or settings.Settings(retries=0), move, log)
	def run_plan(self, plan, log=None):
		codes = []
		for job in plan.jobs:
			planner.recheck(plan, job)
			code, output = windows.run(
				job.arguments(self.executable, plan.settings, plan.move, log),
				timeout=15
			)
			self.assertLess(code, 8, output)
			codes.append(code)
		return codes
	def junction(self, link, target):
		result = subprocess.run(
			[
				os.path.join(os.environ['WINDIR'], 'System32', 'cmd.exe'),
				'/d', '/c', 'mklink', '/J', str(link), str(target)
			],
			capture_output=True, timeout=10
		)
		self.assertEqual(0, result.returncode, repr(result.stdout + result.stderr))
