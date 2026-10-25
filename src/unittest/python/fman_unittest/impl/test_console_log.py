import io
import unittest

from PyQt5.QtTest import QSignalSpy

import fman
from fman.impl.console_log import ConsoleLog, TeeStream, format_log_args


class ConsoleLogTest(unittest.TestCase):
	def test_keeps_only_the_last_entries_in_order(self):
		console_log = ConsoleLog()

		for i in range(ConsoleLog.MAX_ENTRIES + 2):
			console_log.append(str(i))

		self.assertEqual(
			console_log.entries,
			tuple(str(i) for i in range(2, ConsoleLog.MAX_ENTRIES + 2))
		)

	def test_appends_error_as_timestamped_headline_and_traceback(self):
		console_log = ConsoleLog()

		entry = console_log.append_error('Plugin raised an error.', 'Traceback line')

		self.assertRegex(
			entry,
			r'^--- \d{2}:\d{2}:\d{2} Plugin raised an error\. ---\nTraceback line$'
		)
		self.assertEqual(console_log.entries, (entry,))

	def test_emits_appended_entry(self):
		console_log = ConsoleLog()
		spy = QSignalSpy(console_log.entry_added)

		console_log.append('message')

		self.assertEqual(len(spy), 1)
		self.assertEqual(spy[0][0], 'message')

	def test_snapshot_and_subscribe_includes_existing_entries_and_future_entries(self):
		console_log = ConsoleLog()
		console_log.append('existing')
		spy = QSignalSpy(console_log.entry_added)

		entries = console_log.snapshot_and_subscribe(lambda entry: None)
		console_log.append('future')

		self.assertEqual(entries, ('existing',))
		self.assertEqual(len(spy), 1)
		self.assertEqual(spy[0][0], 'future')

	def test_tee_stream_forwards_and_captures_text(self):
		console_log = ConsoleLog()
		original = io.StringIO()
		stream = TeeStream(original, console_log)

		self.assertEqual(stream.write('hello\n'), 6)
		stream.flush()

		self.assertEqual(original.getvalue(), 'hello\n')
		self.assertEqual(console_log.entries, ('hello\n',))

	def test_tee_stream_captures_when_original_is_missing(self):
		console_log = ConsoleLog()
		stream = TeeStream(None, console_log)

		self.assertEqual(stream.write('hello'), 5)
		stream.flush()

		self.assertEqual(console_log.entries, ('hello',))

	def test_formats_log_arguments_like_print(self):
		self.assertEqual(format_log_args('text', 1, None), 'text 1 None\n')
		self.assertEqual(format_log_args(), '\n')

	def test_fman_log_is_public_and_appends_formatted_arguments(self):
		self.assertIn('log', fman.__all__)
		console_log = fman.get_console_log()

		fman.log('text', 1)

		self.assertEqual(console_log.entries[-1], 'text 1\n')


if __name__ == '__main__':
	unittest.main()
