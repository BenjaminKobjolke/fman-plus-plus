from core.undo_history import CopyRecord, MoveRecord, RenameRecord, \
	TrashRecord, history
from unittest import TestCase


class UndoHistoryTest(TestCase):
	def setUp(self):
		history.clear()

	def tearDown(self):
		history.clear()

	def test_records_are_popped_in_last_in_first_out_order(self):
		first = TrashRecord(('file:///a',))
		second = RenameRecord((('file:///b', 'file:///c'),))
		history.record(first)
		history.record(second)

		self.assertIs(second, history.pop())
		self.assertIs(first, history.pop())

	def test_empty_history_returns_none(self):
		self.assertIsNone(history.pop())

	def test_empty_records_are_ignored(self):
		history.record(TrashRecord(()))
		history.record(CopyRecord(()))
		history.record(MoveRecord(()))
		history.record(RenameRecord(()))

		self.assertIsNone(history.pop())
