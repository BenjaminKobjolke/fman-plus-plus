"""A Qt-free Python prompt that sends input and interpreter errors
to the console log."""

from code import InteractiveConsole
import sys
import traceback


class ConsoleInterpreter(InteractiveConsole):
	"""Execute console input in a supplied namespace and log its prompt/errors."""

	def __init__(self, console_log, namespace):
		super().__init__(locals=namespace)
		self._console_log = console_log

	def push(self, line):
		prompt = '... ' if self.buffer else '>>> '
		self._console_log.append('{}{}\n'.format(prompt, line))
		return super().push(line)

	def write(self, data):
		self._console_log.append(data)

	def showtraceback(self):
		self._console_log.append(''.join(traceback.format_exception(*sys.exc_info())))
