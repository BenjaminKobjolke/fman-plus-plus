from collections import namedtuple
from fman.impl.model.table import _get_move_destination, invalidate_icons, \
	DimmedRole, Row as ModelRow, Rows, TableModel
from unittest import TestCase

class GetMoveDestinationTest(TestCase):
	def test_move_one_row_up(self):
		# Example taken from the Qt docs on QAbstractItemModel#beginMoveRows.
		self.assertEqual(0, _get_move_destination(2, 3, 0))
	def test_move_one_row_one_step_down(self):
		# Example taken from the Qt docs on QAbstractItemModel#beginMoveRows.
		self.assertEqual(4, _get_move_destination(2, 3, 3))
	def test_move_multiple_rows_down_overlapping(self):
		self.assertEqual(4, _get_move_destination(1, 3, 2))
	def test_move_multiple_rows_down_adjacent(self):
		self.assertEqual(5, _get_move_destination(1, 3, 3))
	def test_move_multiple_rows_far_down(self):
		self.assertEqual(6, _get_move_destination(1, 3, 4))
	def test_move_multiple_rows_one_up(self):
		self.assertEqual(1, _get_move_destination(2, 101, 1))
	def test_move_multiple_rows_two_up(self):
		self.assertEqual(0, _get_move_destination(2, 101, 0))
	def test_move_multiple_rows_far_up(self):
		self.assertEqual(2, _get_move_destination(5, 7, 2))

class RowEqualityTest(TestCase):

	"""
	Row#__eq__ ignores .icon by value - its docstring says why. The icon
	generation is how a *real* icon change gets through anyway: without it,
	reloading a directory after switching icon set or color produces no diff
	entry, so the panes keep drawing the old icons until you browse elsewhere.
	"""

	def test_same_generation_is_equal(self):
		# Two reloads of an unchanged file. The icons are different objects
		# (QFileIconProvider gives new ones every time) and must not count.
		self.assertEqual(self._row('an icon'), self._row('another icon'))
	def test_new_generation_is_not_equal(self):
		before = self._row('an icon')
		invalidate_icons()
		self.assertNotEqual(before, self._row('another icon'))
	def _row(self, icon):
		return ModelRow('file://C:/dir/notes.txt', icon, False, ('notes.txt',))

class RowsFindTest(TestCase):

	"""
	Rows drops its key -> rownum index on every insert / remove and rebuilds it
	in #find(...). Keeping it current instead cost O(n) per call.
	"""

	def test_find_after_insert_in_front(self):
		self._rows.insert([Row('b'), Row('c')], 0)
		self._rows.insert([Row('a')], 0)
		self._expect_found('a', 'b', 'c')
	def test_find_after_remove(self):
		self._rows.insert([Row('a'), Row('b'), Row('c')], 0)
		self._rows.find('c')
		self._rows.remove(0, 2)
		self._expect_found('c')
		with self.assertRaises(KeyError):
			self._rows.find('a')
	def test_find_after_move(self):
		self._rows.insert([Row('a'), Row('b'), Row('c')], 0)
		self._rows.move(0, 1, 2)
		self._expect_found('b', 'c', 'a')
	def test_find_after_update_and_setitem(self):
		self._rows.insert([Row('a'), Row('b'), Row('c')], 0)
		self._rows.find('a')
		self._rows.update([Row('x')], 1)
		self._rows[2] = Row('y')
		self._expect_found('a', 'x', 'y')
	def _expect_found(self, *keys):
		self.assertEqual(
			list(range(len(keys))), [self._rows.find(key) for key in keys]
		)
	def setUp(self):
		super().setUp()
		self._rows = Rows()

class TableModelTest(TestCase):
	def test_dimmed_role_is_false_without_a_dimmer(self):
		self._model.insert_rows([Row('a')])
		self.assertFalse(self._model.data(self._model.index(0, 0), DimmedRole))
	def test_dimmed_role_follows_the_dimmer(self):
		self._model.insert_rows([Row('hidden'), Row('visible')])
		self._model.set_dimmer(lambda key: key == 'hidden')
		self.assertTrue(self._model.data(self._model.index(0, 0), DimmedRole))
		self.assertFalse(self._model.data(self._model.index(1, 0), DimmedRole))
	def test_set_dimmer_notifies_all_rows(self):
		self._model.insert_rows([Row('a'), Row('b')])
		self._model.dataChanged = StubSignal()
		self._model.set_dimmer(lambda _key: True)
		top_left, bottom_right, roles = self._model.dataChanged.args
		self.assertEqual((0, 0), (top_left.row(), top_left.column()))
		self.assertEqual((1, 0), (bottom_right.row(), bottom_right.column()))
		self.assertEqual([DimmedRole], roles)
	def test_empty(self):
		# Sanity check
		self._expect_rows([])
	def test_insert_first_row(self):
		row = Row('a')
		self._model.insert_rows([row])
		self._expect_rows([row])
	def test_insert_second_row(self):
		a = Row('a')
		self._model.insert_rows([a])
		b = Row('b')
		self._model.insert_rows([b])
		self._expect_rows([a, b])
		return a, b
	def test_insert_at_start(self):
		a, b = self.test_insert_second_row()
		c = Row('c')
		self._model.insert_rows([c], 0)
		self._expect_rows([c, a, b])
	def test_insert_between(self):
		a, b = self.test_insert_second_row()
		c = Row('c')
		self._model.insert_rows([c], 0)
		self._expect_rows([c, a, b])
	def test_move_row_forward(self):
		a, b, c = Row('a'), Row('b'), Row('c')
		self._model.insert_rows([a, b, c])
		self._model.move_rows(0, 1, 1)
		self._expect_rows([b, a, c])
	def test_move_row_end(self):
		a, b, c = Row('a'), Row('b'), Row('c')
		self._model.insert_rows([a, b, c])
		self._model.move_rows(0, 1, 2)
		self._expect_rows([b, c, a])
	def test_move_row_back(self):
		a, b, c = Row('a'), Row('b'), Row('c')
		self._model.insert_rows([a, b, c])
		self._model.move_rows(1, 2, 0)
		self._expect_rows([b, a, c])
	def test_move_multiple_rows(self):
		a, b, c = Row('a'), Row('b'), Row('c')
		self._model.insert_rows([a, b, c])
		self._model.move_rows(0, 2, 1)
		self._expect_rows([c, a, b])
	def test_update(self):
		a, b, c = Row('a'), Row('b'), Row('c')
		self._model.update_rows([a, b], 0)
		self._expect_rows([a, b])
		self._model.update_rows([c], 0)
		self._expect_rows([c, b])
		self._model.update_rows([a], 1)
		self._expect_rows([c, a])
	def test_remove(self):
		a, b, c = Row('a'), Row('b'), Row('c')
		self._model.insert_rows([a, b, c])
		self._model.remove_rows(2)
		self._expect_rows([a, b])
		self._model.remove_rows(0, 1)
		self._expect_rows([b])
		self._model.remove_rows(0, 1)
		self._expect_rows([])
	def setUp(self):
		super().setUp()
		self._model = StubTableModel(['Column 1'])
	def _expect_rows(self, rows):
		self.assertEqual(rows, self._model.get_rows())

class StubSignal:
	def emit(self, *args):
		self.args = args

class StubTableModel(TableModel):

	dataChanged = StubSignal()

	def get_rows(self):
		return list(self._rows)
	def beginInsertRows(self, *args, **kwargs):
		pass
	def endInsertRows(self):
		pass
	def beginMoveRows(self, *args, **kwargs):
		return True
	def endMoveRows(self):
		pass
	def beginRemoveRows(self, *args, **kwargs):
		pass
	def endRemoveRows(self):
		pass
	def index(self, row, column):
		return StubIndex(self, row, column)

class StubIndex:
	def __init__(self, model, row, column):
		self._model, self._row, self._column = model, row, column
	def isValid(self):
		return True
	def model(self):
		return self._model
	def row(self):
		return self._row
	def column(self):
		return self._column

class Row(namedtuple('Row', ('key', 'value'))):
	def __new__(cls, key, value=None):
		return super(Row, cls).__new__(cls, key, value)
