"""Run unittest tests with a timeout that fails a hung test process.

unittest has no per-test timeout, and pytest-timeout is not installed in the
system Python. The Tickets Watcher needs a hung test to fail inside its command
limit.
"""

import faulthandler
import threading
import time
import unittest


TEST_TIMEOUT_SECONDS = 120
PROGRESS_INTERVAL_SECONDS = 30


class TimeoutTestResult(unittest.TextTestResult):
	def startTest(self, test):
		# exit=True ends the process with code 1 and dumps every thread's stack,
		# which includes the hung test's name.
		self.stream.writeln("Running test: {}".format(test.id()))
		self.stream.flush()
		self._test_started_at = time.monotonic()
		self._test_finished = threading.Event()
		self._schedule_progress(test)
		faulthandler.dump_traceback_later(TEST_TIMEOUT_SECONDS, exit=True)
		super().startTest(test)

	def stopTest(self, test):
		self._test_finished.set()
		self._progress_timer.cancel()
		faulthandler.cancel_dump_traceback_later()
		super().stopTest(test)

	def _schedule_progress(self, test):
		self._progress_timer = threading.Timer(
			PROGRESS_INTERVAL_SECONDS, self._report_progress, (test,)
		)
		self._progress_timer.daemon = True
		self._progress_timer.start()

	def _report_progress(self, test):
		if self._test_finished.is_set():
			return
		elapsed = int(time.monotonic() - self._test_started_at)
		self.stream.writeln(
			"Still running: {} ({}s elapsed)".format(test.id(), elapsed)
		)
		self.stream.flush()
		self._schedule_progress(test)


class TimeoutTestRunner(unittest.TextTestRunner):
	resultclass = TimeoutTestResult


def main(argv=None):
	return unittest.main(module=None, argv=argv, testRunner=TimeoutTestRunner)


if __name__ == "__main__":
	main()
