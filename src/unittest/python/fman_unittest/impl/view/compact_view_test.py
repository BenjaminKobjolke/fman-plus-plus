"""Run via tools\\run_view_tests.bat; this suite owns a QApplication."""

from fman.impl.view import FileListView
from fman.impl.view.compact_view import CompactFileView
from fman_unittest.impl.model import StubFileSystem
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock


class StubPaneModel(QStandardItemModel):
	sort_order_changed = pyqtSignal(int, int)
	transaction_ended = pyqtSignal()

	def __init__(self, names):
		super().__init__(len(names), 1)
		self._fs = StubFileSystem({
			'': {'files': names},
			**{'stub://' + name: {'is_dir': False} for name in names}
		})
		names = self._fs.iterdir('')
		self._loaded = set()
		for row, name in enumerate(names):
			item = QStandardItem(name)
			item.setData(name, Qt.ToolTipRole)
			self.setItem(row, 0, item)

	def url(self, index):
		return 'stub://' + self.item(index.row()).text()

	def find(self, url):
		name = url[len('stub://'):]
		for row in range(self.rowCount()):
			if self.item(row).text() == name:
				return self.index(row, 0)
		raise ValueError(url)

	def row_is_loaded(self, row):
		return row in self._loaded

	def get_location(self):
		return 'stub://'

	def load_rows(self, rows, callback=None):
		self._loaded.update(rows)
		if callback:
			callback()


class CompactFileViewTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		names = ['name-%02d.txt' % i for i in range(30)]
		self.model = StubPaneModel(names)
		self.file_view = FileListView(None, lambda *_: [])
		self.file_view.setModel(self.model)
		self.file_view.request_rows = Mock()
		self.view = CompactFileView(self.file_view)
		self.view.resize(240, 180)
		self.view.setModel(self.model)
		self.view.setSelectionModel(self.file_view.selectionModel())
		self.view.show()
		self.app.processEvents()
		self.addCleanup(self.view.deleteLater)
		self.addCleanup(self.file_view.deleteLater)

	def test_layout_fills_columns_top_to_bottom(self):
		self.view.resize(300, 100)
		self.app.processEvents()
		rows_per_column = self.view.viewport().height() // self.view.gridSize().height()
		first = self.view.visualRect(self.model.index(0, 0))
		second_column = self.view.visualRect(self.model.index(rows_per_column, 0))
		self.assertGreater(second_column.x(), first.x())
		self.assertEqual(first.y(), second_column.y())

	def test_grid_width_fits_longest_name_and_caps_at_viewport(self):
		self.view.set_grid_width()
		longest_width = self.view.fontMetrics().horizontalAdvance('name-29.txt')
		self.assertGreaterEqual(self.view.gridSize().width(), longest_width)
		self.assertLessEqual(self.view.gridSize().width(), self.view.viewport().width())
		self.model.item(0).setText('an-extremely-long-filename-that-cannot-fit-in-the-pane.txt')
		self.view.set_grid_width()
		self.assertEqual(self.view.viewport().width(), self.view.gridSize().width())

	def test_grid_width_updates_are_coalesced(self):
		update = Mock(wraps=self.view.set_grid_width)
		self.view.set_grid_width = update
		self.view.schedule_grid_width()
		self.view.schedule_grid_width()
		self.app.processEvents()
		update.assert_called_once_with()

	def test_double_click_invokes_pane_callback(self):
		callback = Mock()
		view = CompactFileView(self.file_view, callback)
		index = self.model.index(0, 0)
		view.doubleClicked.emit(index)
		callback.assert_called_once_with(index)
		view.deleteLater()

	def test_tooltip_is_shown_only_for_elided_names(self):
		self.model.item(0).setText('a-name-that-is-much-too-long-for-the-available-column-width.txt')
		self.view.set_grid_width()
		self.assertEqual(
			self.model.item(0).data(Qt.ToolTipRole),
			self.view.tooltip_text(self.model.index(0, 0)),
		)
		self.assertEqual('', self.view.tooltip_text(self.model.index(1, 0)))

	def test_selection_and_current_index_are_shared_with_file_view(self):
		self.file_view.select(['stub://name-02.txt'])
		self.assertTrue(self.view.selectionModel().isSelected(self.model.index(2, 0)))
		self.file_view.setCurrentIndex(self.model.index(4, 0))
		self.assertEqual(self.model.index(4, 0), self.view.currentIndex())

	def test_paint_requests_only_visible_unloaded_rows(self):
		self.view.resize(240, 80)
		self.app.processEvents()
		self.view.repaint()
		self.assertTrue(self.file_view.request_rows.called)
		rows = self.file_view.request_rows.call_args.args[0]
		self.assertTrue(rows)
		self.assertTrue(all(0 <= row < self.model.rowCount() for row in rows))
		self.assertLess(len(rows), self.model.rowCount())

	def test_key_filter_handles_left_before_default_navigation(self):
		self.view.setCurrentIndex(self.model.index(5, 0))
		self.view.key_press_event_filter = Mock(return_value=True)
		event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Left, Qt.NoModifier)
		self.view.keyPressEvent(event)
		self.view.key_press_event_filter.assert_called_once_with(event)
		self.assertEqual(self.model.index(5, 0), self.view.currentIndex())

	def test_shift_end_selects_linear_rows_through_last_item(self):
		self.view.setCurrentIndex(self.model.index(0, 0))
		event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_End, Qt.ShiftModifier)
		self.view.keyPressEvent(event)
		self.assertEqual(list(range(self.model.rowCount())), sorted(
			index.row() for index in self.view.selectionModel().selectedRows()
		))
