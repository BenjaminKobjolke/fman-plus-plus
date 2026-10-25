"""Check that the shared unittest runner propagates failures and kills hangs."""

import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run_runner(tools_directory, tests_directory, test_name):
	code = (
		"import sys; "
		f"sys.path.insert(0, {str(tools_directory)!r}); "
		"import unittest_with_timeout; "
		"unittest_with_timeout.TEST_TIMEOUT_SECONDS = 2; "
		f"unittest_with_timeout.main(['runner', 'discover', "
		f"'-s', {str(tests_directory)!r}, "
		f"'-k', {test_name!r}])"
	)
	started = time.monotonic()
	result = subprocess.run(
		[sys.executable, "-c", code],
		stdin=subprocess.DEVNULL,
		capture_output=True,
		text=True,
		timeout=60,
	)
	return result, time.monotonic() - started


def check_unittest_with_timeout():
	tools_directory = Path(__file__).resolve().parent
	with tempfile.TemporaryDirectory(prefix="unittest-timeout-") as temporary:
		tests_directory = Path(temporary)
		(tests_directory / "test_sample.py").write_text(
			"import time\n"
			"import unittest\n\n"
			"class SampleTest(unittest.TestCase):\n"
			"    def test_passes(self):\n"
			"        self.assertTrue(True)\n\n"
			"    def test_fails(self):\n"
			"        self.fail('expected failure')\n\n"
			"    def test_sleeps(self):\n"
			"        time.sleep(30)\n",
			encoding="utf-8",
		)

		result, _ = run_runner(tools_directory, tests_directory, "test_passes")
		assert result.returncode == 0, result.stdout + result.stderr

		result, _ = run_runner(tools_directory, tests_directory, "test_fails")
		assert result.returncode == 1, result.stdout + result.stderr

		result, elapsed = run_runner(tools_directory, tests_directory, "test_sleeps")
		assert result.returncode != 0, result.stdout + result.stderr
		assert "Timeout" in result.stderr, result.stdout + result.stderr
		assert "test_sleeps" in result.stderr, result.stdout + result.stderr
		assert "Running test: test_sample.SampleTest.test_sleeps" in result.stderr, (
			result.stdout + result.stderr
		)
		assert elapsed < 30, f"The sleeping test ran for {elapsed:.1f} seconds"


if __name__ == "__main__":
	check_unittest_with_timeout()
	print("unittest with timeout OK")
