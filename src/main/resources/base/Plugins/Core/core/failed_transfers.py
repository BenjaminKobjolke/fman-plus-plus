"""Collect transfer tasks that failed and may be retried after the operation."""

from core.skipped_errors import SkippedErrors
from threading import Lock


class FailedTransfers:
	def __init__(self):
		self._failures = []
		self._lock = Lock()

	def record(self, task, failure):
		with self._lock:
			self._failures.append((task, failure))

	def take(self):
		with self._lock:
			failures = self._failures
			self._failures = []
		return failures

	@classmethod
	def message(cls, title, failures):
		count = len(failures)
		word = 'file' if count == 1 else 'files'
		retry = 'it' if count == 1 else 'them'
		lines = [
			SkippedErrors._elide(failure)
			for _, failure in failures[:SkippedErrors.MAX_EXAMPLES]
		]
		remaining = count - len(lines)
		if remaining:
			lines.append('... and {:,} more.'.format(remaining))
		return '{}: {:,} {} failed.\n\n{}\n\nRetry {}?'.format(
			title, count, word, '\n'.join(lines), retry
		)
