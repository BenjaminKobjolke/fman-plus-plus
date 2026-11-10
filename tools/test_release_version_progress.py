"""Check that release handoff test steps report progress before running."""

import io
import subprocess
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import test_release_version


class RunBatchProgressTest(unittest.TestCase):
    def test_reports_batch_before_running_it(self):
        output = io.StringIO()

        def run_batch(*args, **kwargs):
            self.assertIn("Running batch: build_release.bat", output.getvalue())
            return subprocess.CompletedProcess(args[0], 0, "", "")

        with patch.object(subprocess, "run", side_effect=run_batch):
            with redirect_stdout(output):
                result = test_release_version.run_batch(Path("build_release.bat"))

        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
