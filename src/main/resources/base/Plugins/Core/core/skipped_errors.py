"""Collect file-operation failures skipped by choosing Yes to all."""


class SkippedErrors:
	MAX_EXAMPLES = 10
	MAX_EXAMPLE_LENGTH = 200

	def __init__(self):
		self._silent_count = 0
		self._examples = []

	def record(self, failure, silent):
		if not silent:
			return
		self._silent_count += 1
		if len(self._examples) < self.MAX_EXAMPLES:
			self._examples.append(self._elide(failure))

	def report(self, title):
		if not self._silent_count:
			return None
		count = self._silent_count
		self._silent_count = 0
		word = 'error was' if count == 1 else 'errors were'
		lines = self._examples[:]
		remaining = count - len(lines)
		if remaining:
			lines.append('... and {:,} more.'.format(remaining))
		self._examples = []
		return '{}: {:,} {} skipped.\n\n{}'.format(
			title, count, word, '\n'.join(lines)
		)

	@classmethod
	def _elide(cls, failure):
		if len(failure) <= cls.MAX_EXAMPLE_LENGTH:
			return failure
		remaining = cls.MAX_EXAMPLE_LENGTH - 1
		start = remaining // 2
		end = remaining - start
		return failure[:start] + '…' + failure[-end:]
