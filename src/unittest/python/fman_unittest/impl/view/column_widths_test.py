"""Run via tools\\run_view_tests.bat; this suite owns a QApplication."""

from fman.impl.view import FileListView
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import patch


class Name:
	@classmethod
	def qualified_name(cls):
		return 'columns.Name'
	get_qualified_name = qualified_name

	@classmethod
	def get_widest_str(cls):
		return ''

class Size:
	@classmethod
	def qualified_name(cls):
		return 'columns.Size'
	get_qualified_name = qualified_name

	@classmethod
	def get_widest_str(cls):
		return '999.9 MB'

class Modified:
	@classmethod
	def qualified_name(cls):
		return 'columns.Modified'
	get_qualified_name = qualified_name

	@classmethod
	def get_widest_str(cls):
		return '28/12/00 22:58'


class ColumnModel(QStandardItemModel):
	sort_order_changed = pyqtSignal(int, int)
	transaction_ended = pyqtSignal()

	def __init__(self, rows=1):
		super().__init__(rows, 3)
		self._columns = [Name, Size, Modified]
		self._loaded = True
		for row in range(rows):
			self.setRow(row, 'a', '1 KB', '1/1/00')

	def get_columns(self):
		return self._columns

	def row_is_loaded(self, row):
		return self._loaded

	def url(self, index):
		return str(index.row())

	def load_rows(self, rows, callback=None):
		self._loaded = True
		if callback:
			callback()

	def set_num_rows_to_preload(self, _):
		pass

	def reset_while_loading(self):
		self._loaded = False
		self.beginResetModel()
		self.endResetModel()

	def setRow(self, row, name, size, modified):
		for column, value in enumerate((name, size, modified)):
			self.setItem(row, column, QStandardItem(value))


class FileListColumnWidthsTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.view = FileListView(None, lambda *_: [])
		self.model = ColumnModel()
		self.view.setModel(self.model)
		self.view.resize(700, 280)
		self.view.show()
		self.app.processEvents()
		self.addCleanup(self.view.deleteLater)

	def test_fixed_sample_widths_do_not_follow_folder_contents(self):
		self.view.fit_name_column = False
		self.view.resizeColumnsToContents()
		widths = self.view._get_column_widths()
		model = self.view.model()
		model.setRow(0, 'a very long file name', '999.9 MB', '28/12/00 22:58')
		model.beginResetModel()
		model.endResetModel()
		self.app.processEvents()
		self.view.resizeColumnsToContents()
		self.assertEqual(widths[1:], self.view._get_column_widths()[1:])

	def test_scrollbar_visibility_does_not_change_available_width(self):
		self.assertEqual(
			self.view.width() - self.view.verticalScrollBar().sizeHint().width(),
			self.view._get_width_excl_scrollbar()
		)

	def test_scrollbar_starts_below_header(self):
		from PyQt5.QtWidgets import QTableView, QWidget
		from fman.impl.view.scrollbar_below_header import \
			install_scrollbar_below_header

		view = QTableView()
		view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		view.resize(300, 200)
		view.show()
		install_scrollbar_below_header(view)
		self.app.processEvents()
		scrollbar_top = view.verticalScrollBar().mapTo(
			view, QPoint(0, 0)
		).y()
		header_bottom = view.horizontalHeader().mapTo(
			view, QPoint(0, view.horizontalHeader().height())
		).y()
		self.assertGreaterEqual(scrollbar_top, header_bottom)
		spacer = view.findChild(QWidget, 'scrollbar_header_spacer')
		header = view.horizontalHeader()
		header.setFixedHeight(header.height() + 10)
		self.app.processEvents()
		self.assertEqual(header.height(), spacer.height())
		view.deleteLater()

	def test_reset_restores_widths_while_rows_are_loading(self):
		self.view._handle_col_resize = False
		self.view.setColumnWidth(1, 137)
		self.view._handle_col_resize = True
		self.view.hide()
		self.view.model().reset_while_loading()
		self.app.processEvents()
		self.assertEqual(137, self.view.columnWidth(1))

	def test_inserted_rows_schedule_a_refit(self):
		self.view.resizeColumnsToContents()
		before = self.view.sizeHintForColumn(1)
		model = self.view.model()
		model.insertRow(model.rowCount())
		model.setRow(model.rowCount() - 1, 'name', 'a much wider file size', 'date')
		self.app.processEvents()
		self.assertGreaterEqual(self.view.sizeHintForColumn(1), before)

	def test_dragged_widths_round_trip_and_ignore_invalid_values(self):
		self.view.set_dragged_widths({
			'columns.Name': 300, 'columns.Size': 125,
			'columns.Modified': 'wide', 'invalid': None,
		})
		self.assertEqual(
			{'columns.Name': 300, 'columns.Size': 125},
			self.view.get_dragged_widths()
		)
		with patch(
			'fman.impl.view.resize_cols_to_contents.QApplication',
			mouseButtons=lambda: Qt.LeftButton
		):
			self.view.horizontalHeader().sectionResized.emit(1, 100, 141)
		self.assertEqual(
			self.view.columnWidth(1),
			self.view.get_dragged_widths()['columns.Size']
		)
