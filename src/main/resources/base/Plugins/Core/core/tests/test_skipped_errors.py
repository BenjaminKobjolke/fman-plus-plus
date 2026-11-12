from core.skipped_errors import SkippedErrors
from unittest import TestCase


class SkippedErrorsTest(TestCase):
	def test_report_is_none_when_no_failure_was_skipped_silently(self):
		errors = SkippedErrors()
		errors.record('Error copying first.txt.', silent=False)
		self.assertIsNone(errors.report('Copying 1 files'))

	def test_report_counts_silent_errors_with_singular_and_plural_text(self):
		errors = SkippedErrors()
		errors.record('Error copying first.txt.', silent=True)
		self.assertEqual(
			'Copying 1 files: 1 error was skipped.\n\n'
			'Error copying first.txt.',
			errors.report('Copying 1 files'),
		)

		errors.record('Error copying second.txt.', silent=True)
		errors.record('Error copying third.txt.', silent=True)
		self.assertEqual(
			'Copying 3 files: 2 errors were skipped.\n\n'
			'Error copying second.txt.\nError copying third.txt.',
			errors.report('Copying 3 files'),
		)

	def test_report_caps_examples_and_counts_the_rest(self):
		errors = SkippedErrors()
		for i in range(12):
			errors.record('Error copying %d.txt.' % i, silent=True)
		report = errors.report('Copying files')
		self.assertIn('12 errors were skipped.', report)
		self.assertEqual(10, report.count('Error copying'))
		self.assertIn('... and 2 more.', report)

	def test_examples_are_elided_in_the_middle(self):
		errors = SkippedErrors()
		failure = 'start' + ('x' * 250) + 'end'
		errors.record(failure, silent=True)
		report = errors.report('Moving files')
		self.assertIn('…', report)
		self.assertLessEqual(len(report.splitlines()[-1]), 200)

	def test_report_is_emitted_only_once(self):
		errors = SkippedErrors()
		errors.record('Error moving file.txt.', silent=True)
		self.assertIsNotNone(errors.report('Moving files'))
		self.assertIsNone(errors.report('Moving files'))
