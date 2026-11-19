"""Run unittest tests with a timeout that fails a hung test process.

unittest has no per-test timeout, and pytest-timeout is not installed in the
system Python. The Tickets Watcher needs a hung test to fail inside its command
limit.
"""

import atexit
import faulthandler
import os
import sys
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
	faulthandler.enable()
	# Registered first so this runs after every other exit handler.
	atexit.register(_skip_interpreter_teardown)
	try:
		return unittest.main(module=None, argv=argv, testRunner=TimeoutTestRunner)
	except SystemExit as exit_request:
		code = exit_request.code
		if code is None:
			_skip_interpreter_teardown.exit_code = 0
		elif isinstance(code, int):
			_skip_interpreter_teardown.exit_code = code
		else:
			_skip_interpreter_teardown.exit_code = 1
		# Imported test modules may register shutdown handlers that destroy Qt
		# objects. Exit before those handlers run, as well as before interpreter
		# teardown, to avoid a native crash after the test summary.
		_skip_interpreter_teardown()


def _skip_interpreter_teardown():
	# Destroying PyQt objects during interpreter teardown can crash in sip
	# (see fman/main.py).
	try:
		for stream in (sys.stdout, sys.stderr):
			if stream is not None:
				try:
					stream.flush()
				except (OSError, ValueError):
					pass
	finally:
		os._exit(_skip_interpreter_teardown.exit_code)


_skip_interpreter_teardown.exit_code = 1


if __name__ == "__main__":
	main()
