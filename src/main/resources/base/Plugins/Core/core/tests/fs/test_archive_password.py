from core.fs import archive_password
from fman import Task
from unittest import TestCase
from unittest.mock import Mock, patch

class ArchivePasswordTest(TestCase):
	def tearDown(self):
		archive_password.clear()
	def test_password_is_stored_by_normalized_case_insensitive_path(self):
		archive_password.remember_password('Archives/../Protected.ZIP', 'secret')
		self.assertEqual(
			'secret', archive_password.get_password('protected.zip')
		)
	def test_classifies_each_7zip_password_failure_message(self):
		outputs = (
			'Enter password (will not be echoed):\nBreak signaled',
			'ERROR: Wrong password : a.txt',
			'Data Error in encrypted file. Wrong password? : a.txt'
		)
		for output in outputs:
			with self.subTest(output=output):
				self.assertTrue(archive_password.is_password_error(output))
	def test_does_not_classify_an_ordinary_error_as_a_password_failure(self):
		self.assertFalse(archive_password.is_password_error(
			'ERROR: Data Error : a.txt'
		))
	def test_cancelling_password_prompt_cancels_task(self):
		task = Mock()
		task.show_prompt.return_value = ('', False)
		with self.assertRaises(Task.Canceled):
			archive_password.ask_password('archive.zip', task)
		task.show_prompt.assert_called_once_with(
			'Password for archive.zip:', password=True
		)
	def test_prompt_falls_back_to_main_ui_for_direct_task_calls(self):
		task = Mock()
		task.show_prompt.side_effect = NotImplementedError
		with patch.object(
			archive_password, 'show_prompt', return_value=('secret', True)
		) as prompt:
			self.assertEqual(
				'secret', archive_password.ask_password('archive.zip', task)
			)
		prompt.assert_called_once_with(
			'Password for archive.zip:', password=True
		)
