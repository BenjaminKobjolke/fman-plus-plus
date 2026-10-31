from unittest import TestCase
from unittest.mock import Mock

from core.transfer_completion import TransferCompletion


class TransferCompletionTest(TestCase):
	def test_items_complete_after_their_last_task_in_any_order(self):
		on_item_done = Mock()
		completion = TransferCompletion(on_item_done)
		first_task, second_task, other_task = object(), object(), object()

		completion.begin_item('first')
		completion.add_task(first_task)
		completion.add_task(second_task)
		completion.end_item()
		completion.begin_item('other')
		completion.add_task(other_task)
		completion.end_item()

		completion.task_finished(other_task, True)
		completion.task_finished(second_task, True)
		completion.task_finished(first_task, True)

		self.assertEqual(2, on_item_done.call_count)
		self.assertEqual(['other', 'first'], [
			call.args[0] for call in on_item_done.call_args_list
		])

	def test_tasks_finished_before_end_fire_when_gathering_ends(self):
		on_item_done = Mock()
		completion = TransferCompletion(on_item_done)
		task = object()
		completion.begin_item('item')
		completion.add_task(task)
		completion.task_finished(task, True)

		on_item_done.assert_not_called()
		completion.end_item()
		on_item_done.assert_called_once_with('item')

	def test_item_without_tasks_fires_when_gathering_ends(self):
		on_item_done = Mock()
		completion = TransferCompletion(on_item_done)
		completion.begin_item('empty')
		completion.end_item()
		on_item_done.assert_called_once_with('empty')

	def test_failed_task_keeps_its_item_selected(self):
		on_item_done = Mock()
		completion = TransferCompletion(on_item_done)
		failed_task, successful_task = object(), object()
		completion.begin_item('failed')
		completion.add_task(failed_task)
		completion.end_item()
		completion.begin_item('successful')
		completion.add_task(successful_task)
		completion.end_item()

		completion.task_finished(failed_task, False)
		completion.task_finished(successful_task, True)

		on_item_done.assert_called_once_with('successful')

	def test_marked_incomplete_item_does_not_fire(self):
		on_item_done = Mock()
		completion = TransferCompletion(on_item_done)
		completion.begin_item('skipped')
		completion.mark_incomplete()
		completion.end_item()
		on_item_done.assert_not_called()

	def test_item_canceled_during_gathering_does_not_fire(self):
		on_item_done = Mock()
		completion = TransferCompletion(on_item_done)
		task = object()
		completion.begin_item('canceled')
		completion.add_task(task)

		completion.task_finished(task, True)

		on_item_done.assert_not_called()
