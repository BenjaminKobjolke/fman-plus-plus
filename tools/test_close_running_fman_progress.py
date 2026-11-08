"""Check that the close-running-fman test reports progress immediately."""

import io
import subprocess
import unittest
from unittest.mock import patch

from test_close_running_fman import report_progress, run_helper


class ReportProgressTest(unittest.TestCase):
    def test_writes_and_flushes_progress_line(self):
        class FlushTrackingOutput(io.StringIO):
            flushed = False

            def flush(self):
                self.flushed = True
                super().flush()

        output = FlushTrackingOutput()
        with patch("sys.stdout", output):
            report_progress("Checking process shutdown")

        self.assertEqual(output.getvalue(), "Checking process shutdown\n")
        self.assertTrue(output.flushed)


class RunHelperProgressTest(unittest.TestCase):
    def test_reports_elapsed_time_while_helper_is_running(self):
        class SlowProcess:
            returncode = 0

            def __init__(self):
                self.calls = 0

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def communicate(self, timeout):
                self.calls += 1
                if self.calls == 1:
                    raise subprocess.TimeoutExpired("powershell", timeout)
                return "helper output", ""

        output = io.StringIO()
        process = SlowProcess()
        with patch("sys.stdout", output), \
                patch(
                    "test_close_running_fman.subprocess.Popen",
                    return_value=process,
                ), \
                patch(
                    "test_close_running_fman.time.monotonic",
                    side_effect=[100, 130, 130, 130],
                ):
            result = run_helper("build", 1, "Checking process shutdown")

        self.assertIn(
            "Checking process shutdown (still running after 30 s)", output.getvalue()
        )
        self.assertEqual(result.stdout, "helper output")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
