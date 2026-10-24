"""Check that the close-running-fman test reports progress immediately."""

import io
import unittest
from unittest.mock import patch

from test_close_running_fman import report_progress


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


if __name__ == "__main__":
    unittest.main()
