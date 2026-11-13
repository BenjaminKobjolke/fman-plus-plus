from fman.impl.model.coloring import ColorRole, safe_color
from fman.impl.model.table import Row, TableModel
from PyQt5.QtGui import QColor
from unittest import TestCase
from unittest.mock import patch


class SafeColorTest(TestCase):
	def test_returns_none_without_a_colorer_or_color(self):
		self.assertIsNone(safe_color(None, 'file:///a'))
		self.assertIsNone(safe_color(lambda _url: None, 'file:///a'))

	def test_returns_only_valid_qcolors(self):
		color = QColor('#abcdef')
		self.assertEqual(color, safe_color(lambda _url: color, 'file:///a'))
		self.assertIsNone(
			safe_color(lambda _url: 'red', 'file:///a')
		)
		self.assertIsNone(
			safe_color(lambda _url: QColor('not-a-color'), 'file:///a')
		)

	def test_catches_and_reports_each_colorer_only_once(self):
		def colorer(_url):
			raise ValueError('broken colorer')
		with patch('fman.impl.model.coloring.traceback.print_exc') as print_exc:
			self.assertIsNone(safe_color(colorer, 'file:///a'))
			self.assertIsNone(safe_color(colorer, 'file:///b'))
		self.assertEqual(1, print_exc.call_count)

	def test_color_role_is_a_distinct_user_role(self):
		self.assertEqual(0x0100 + 3, ColorRole)


class TableModelColoringTest(TestCase):
	def test_color_role_uses_row_key_and_colorer(self):
		self.model.insert_rows([Row('file:///a', None, False, [])])
		color = QColor('#abcdef')
		self.model.set_colorer(lambda url: color if url == 'file:///a' else None)
		self.assertEqual(color, self.model.data(self.model.index(0, 0), ColorRole))

	def test_set_colorer_notifies_all_rows(self):
		self.model.insert_rows([
			Row('file:///a', None, False, []),
			Row('file:///b', None, False, [])
		])
		self.model.dataChanged = StubSignal()
		self.model.set_colorer(lambda _url: QColor('#abcdef'))
		top_left, bottom_right, roles = self.model.dataChanged.args
		self.assertEqual((0, 0), (top_left.row(), top_left.column()))
		self.assertEqual((1, 0), (bottom_right.row(), bottom_right.column()))
		self.assertEqual([ColorRole], roles)

	def setUp(self):
		super().setUp()
		self.model = StubTableModel()


class StubTableModel(TableModel):
	dataChanged = None

	def __init__(self):
		self.dataChanged = StubSignal()
		super().__init__(['Name'])

	def beginInsertRows(self, *_args):
		pass

	def endInsertRows(self):
		pass

	def index(self, row, column):
		return StubIndex(self, row, column)


class StubSignal:
	def emit(self, *args):
		self.args = args


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
