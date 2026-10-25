import io
from contextlib import redirect_stdout
from unittest import TestCase

from core.console_interpreter import ConsoleInterpreter
from core.commands.console import ShowConsole, ShowConsoleWindow
from fman.impl.console_log import ConsoleLog, TeeStream
from fman.impl.plugins.plugin import _get_command_name


class ConsoleInterpreterTest(TestCase):

	def test_core_commands_have_the_expected_names(self):
		self.assertEqual('show_console', _get_command_name(ShowConsole))
		self.assertEqual(
			'show_console_window', _get_command_name(ShowConsoleWindow)
		)

	def setUp(self):
		self.console_log = ConsoleLog()
		self.output = io.StringIO()
		self.interpreter = ConsoleInterpreter(self.console_log, {})

	def _push(self, line):
		with redirect_stdout(TeeStream(self.output, self.console_log)):
			return self.interpreter.push(line)

	def test_printed_output_is_captured_by_the_tee_stream(self):
		self._push("print('hello')")
		self.assertIn('hello\n', self.output.getvalue())
		self.assertIn('hello\n', ''.join(self.console_log.entries))

	def test_input_is_echoed_and_tracebacks_are_logged(self):
		self._push('1 / 0')
		entries = ''.join(self.console_log.entries)
		self.assertIn('>>> 1 / 0', entries)
		self.assertIn('ZeroDivisionError', entries)

	def test_multiline_input_uses_continuation_prompt(self):
		self.assertTrue(self._push('for number in range(2):'))
		self.assertTrue(self._push('    print(number)'))
		self.assertFalse(self._push(''))
		entries = ''.join(self.console_log.entries)
		self.assertIn('>>> for number in range(2):', entries)
		self.assertIn('...     print(number)', entries)
		self.assertIn('0\n1\n', self.output.getvalue())

	def test_executes_in_the_supplied_namespace(self):
		self.interpreter.locals['answer'] = 42
		self._push('print(answer)')
		self.assertIn('42\n', self.output.getvalue())
