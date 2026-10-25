"""Run unittest tests with a timeout that fails a hung test process.

unittest has no per-test timeout, and pytest-timeout is not installed in the
system Python. The Tickets Watcher needs a hung test to fail inside its command
limit.
"""

import faulthandler
import unittest


TEST_TIMEOUT_SECONDS = 120


class TimeoutTestResult(unittest.TextTestResult):
	def startTest(self, test):
		# exit=True ends the process with code 1 and dumps every thread's stack,
		# which includes the hung test's name.
		self.stream.writeln("Running test: {}".format(test.id()))
		self.stream.flush()
		faulthandler.dump_traceback_later(TEST_TIMEOUT_SECONDS, exit=True)
		super().startTest(test)

	def stopTest(self, test):
		faulthandler.cancel_dump_traceback_later()
		super().stopTest(test)


class TimeoutTestRunner(unittest.TextTestRunner):
	resultclass = TimeoutTestResult


def main(argv=None):
	return unittest.main(module=None, argv=argv, testRunner=TimeoutTestRunner)


if __name__ == "__main__":
	main()
