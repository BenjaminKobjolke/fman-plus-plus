import unittest

from fman.impl.util.qt import ControlModifier, CopyAction, MoveAction, ShiftModifier
from fman.impl.drop_action import choose_drop_action, volume_of


class DropActionTest(unittest.TestCase):
	def test_cross_drive_defaults_to_copy(self):
		self.assertEqual(
			choose_drop_action(0, ['file:///C:/a.txt'], 'file:///D:/x'),
			CopyAction
		)

	def test_same_drive_defaults_to_move(self):
		self.assertEqual(
			choose_drop_action(0, ['file:///C:/a.txt'], 'file:///C:/x'),
			MoveAction
		)

	def test_drive_comparison_is_case_insensitive(self):
		self.assertEqual(volume_of('file:///c:/a.txt'), volume_of('file:///C:/x'))

	def test_control_copies_and_shift_moves(self):
		src = ['file:///C:/a.txt']
		self.assertEqual(
			choose_drop_action(ControlModifier, src, 'file:///C:/x'), CopyAction
		)
		self.assertEqual(
			choose_drop_action(ShiftModifier, src, 'file:///D:/x'), MoveAction
		)
		self.assertEqual(
			choose_drop_action(ControlModifier | ShiftModifier, src, 'file:///D:/x'),
			CopyAction
		)

	def test_unc_share_is_a_volume(self):
		self.assertEqual(
			choose_drop_action(0, ['file:////server/share/a'], 'file:///C:/x'),
			CopyAction
		)
		self.assertEqual(
			choose_drop_action(
				0, ['file:////server/share/a'], 'file:////server/share/folder'
			),
			MoveAction
		)

	def test_any_cross_volume_source_makes_drop_copy(self):
		self.assertEqual(
			choose_drop_action(
				0,
				['file:///C:/a.txt', 'file:///D:/b.txt'],
				'file:///C:/x'
			),
			CopyAction
		)

	def test_different_url_schemes_are_different_volumes(self):
		self.assertEqual(
			choose_drop_action(0, ['zip:///C:/a.zip/f'], 'file:///C:/x'),
			CopyAction
		)
		self.assertEqual(
			choose_drop_action(0, ['zip:///C:/a.zip/f'], 'zip:///C:/b.zip/x'),
			MoveAction
		)

	def test_missing_destination_uses_modifier_only(self):
		self.assertEqual(choose_drop_action(ControlModifier, [], None), CopyAction)
		self.assertEqual(choose_drop_action(0, ['file:///C:/a'], None), MoveAction)
		self.assertEqual(choose_drop_action(ShiftModifier, [], None), MoveAction)


if __name__ == '__main__':
	unittest.main()
