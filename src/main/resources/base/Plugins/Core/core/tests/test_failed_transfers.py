from core.failed_transfers import FailedTransfers
from core.skipped_errors import SkippedErrors
from unittest import TestCase
from unittest.mock import patch
from fman import YES, NO, Task
from fman.url import join


class FailedTransfersTest(TestCase):
	def test_message_uses_singular_and_plural_wording(self):
		failures = [('task', 'Error copying first.txt (permission denied).')]
		self.assertEqual(
			'Copying 1 files: 1 file failed.\n\n'
			'Error copying first.txt (permission denied).\n\nRetry it?',
			FailedTransfers.message('Copying 1 files', failures),
		)
		failures.append(('other task', 'Error copying second.txt (permission denied).'))
		self.assertEqual(
			'Copying 2 files: 2 files failed.\n\n'
			'Error copying first.txt (permission denied).\n'
			'Error copying second.txt (permission denied).\n\nRetry them?',
			FailedTransfers.message('Copying 2 files', failures),
		)

	def test_message_caps_and_elides_failure_examples(self):
		failures = [
			(object(), 'Failure %d: %s' % (i, 'x' * 250))
			for i in range(SkippedErrors.MAX_EXAMPLES + 2)
		]
		message = FailedTransfers.message('Copying files', failures)
		failure_lines = message.split('\n\n')[1].splitlines()
		self.assertEqual(SkippedErrors.MAX_EXAMPLES + 1, len(failure_lines))
		self.assertIn('…', failure_lines[0])
		self.assertEqual(len(failure_lines[0]), SkippedErrors.MAX_EXAMPLE_LENGTH)
		self.assertEqual('... and 2 more.', failure_lines[-1])
		self.assertTrue(message.endswith('Retry them?'))

	def test_take_returns_recorded_pairs_and_clears_them(self):
		failed = FailedTransfers()
		first = (object(), 'first failure')
		second = (object(), 'second failure')
		failed.record(*first)
		failed.record(*second)
		self.assertEqual([first, second], failed.take())
		self.assertEqual([], failed.take())


class FailedTransferOperationsTestMixin:
	def test_failed_transfer_prompts_once_at_end_after_other_files_copy(self):
		first, second, third = self._make_sources()
		self._expect_failed_transfers_prompt(1, NO)
		_, attempts = self._run_with_transfer_failure(second)
		self.assertEqual(1, attempts[second])
		for name in ('first', 'third'):
			self.assertTrue(self._fs.exists(join(self.dest, name + '.txt')))
		self.assertFalse(self._fs.exists(join(self.dest, 'second.txt')))
	def test_yes_retries_failed_task_and_does_not_prompt_again_when_it_succeeds(self):
		first, second, third = self._make_sources()
		self._expect_failed_transfers_prompt(1, YES)
		_, attempts = self._run_with_transfer_failure(second, retry_succeeds=True)
		self.assertEqual(2, attempts[second])
		self.assertTrue(self._fs.exists(join(self.dest, 'second.txt')))
	def test_failed_retry_is_offered_again_and_no_stops_retrying(self):
		first, second, third = self._make_sources()
		self._expect_failed_transfers_prompt(1, YES)
		self._expect_failed_transfers_prompt(1, NO)
		_, attempts = self._run_with_transfer_failure(second)
		self.assertEqual(2, attempts[second])
	def test_retry_progress_does_not_count_failed_task_twice(self):
		first, second, third = self._make_sources()
		self._expect_failed_transfers_prompt(1, YES)
		operation, _ = self._run_with_transfer_failure(second, retry_succeeds=True)
		self.assertEqual(operation.get_size(), operation.get_progress())
	def test_canceled_operation_does_not_prompt_to_retry_failures(self):
		first, second, third = self._make_sources()
		_, attempts = self._run_with_transfer_failure(
			second, cancel_after_failure=True
		)
		self.assertEqual(1, attempts[second])
	def _expect_failed_transfers_prompt(self, count, answer):
		verb = self.operation_descr_verb
		if verb.endswith('e'):
			verb = verb[:-1]
		verb += 'ing'
		self._expect_alert((
			'%s 3 files: %d file%s failed.\n\n'
			'Error %s second.txt (permission denied).\n\n'
			'%s' % (
				verb.capitalize(), count, '' if count == 1 else 's', verb,
				'Retry it?' if count == 1 else 'Retry them?'
			), YES | NO, YES
		), answer, button_texts={YES: 'Yes', NO: 'No'})
	def _run_with_transfer_failure(
		self, failed_src, retry_succeeds=False, cancel_after_failure=False
	):
		if hasattr(self._fs, '_backends'):
			backend = next(iter(self._fs._backends.values()))
			transfer_name = 'copy'
		else:
			backend = self._fs._children['file://']
			transfer_name = '_rename'
		transfer = getattr(backend, transfer_name)
		attempts = {failed_src: 0}
		def copy_or_fail(src_url, dst_url):
			if src_url == failed_src:
				attempts[src_url] += 1
				if attempts[src_url] == 1 or not retry_succeeds:
					if cancel_after_failure:
						self._progress_dialog.canceled = True
					raise OSError(13, 'permission denied')
			transfer(src_url, dst_url)
		with patch.object(backend, transfer_name, side_effect=copy_or_fail):
			operation = self.operation(
				[
					join(self.src, name + '.txt')
					for name in ('first', 'second', 'third')
				],
				self.dest, fs=self._fs
			)
			operation._get_worker_count = lambda: 1
			operation._dialog = self._progress_dialog
			if cancel_after_failure:
				with self.assertRaises(Task.Canceled):
					operation()
			else:
				operation()
		self._progress_dialog.verify_expected_dialogs_were_shown()
		return operation, attempts
