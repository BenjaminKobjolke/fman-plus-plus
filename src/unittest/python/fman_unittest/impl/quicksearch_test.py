from unittest import TestCase
import threading

from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QColor, QFont, QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QWidget

from fman import QuicksearchItem, QuicksearchExit
from fman.impl.quicksearch import Quicksearch
from fman.impl.quicksearch_elide import elide_title_left, shift_highlight


_CSS = {
	'border-top-width_px': 0,
	'border-bottom-width_px': 1,
	'padding-top_px': 5,
	'padding-left_px': 7,
	'padding-right_px': 7,
	'title': {
		'font-size_pts': 11,
		'color': QColor('#fff'),
		'highlight': {'color': QColor('#f00')},
	},
	'hint': {'font-size_pts': 9, 'color': QColor('#aaa')},
	'description': {'font-size_pts': 9, 'color': QColor('#aaa')},
}


class QuicksearchTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.parent = QWidget()
		self.parent.resize(1600, 900)
		self.parent.setStyleSheet('QListView { min-width: 400px; }')
		self.parent.show()
		self.app.processEvents()
		self.dialog = Quicksearch(
			self.parent, _StubApp(), {}, lambda _query: []
		)
		self.app.processEvents()

	def tearDown(self):
		self.dialog.close()
		self.parent.close()
		self.app.processEvents()

	def _dialog_with_long_items(self, count):
		items = [
			QuicksearchItem(
				'C:/' + '/very_long_folder_name' * 8 + str(i), hint='hint'
			)
			for i in range(count)
		]
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, lambda _query: items
		)
		dialog.show()
		self.app.processEvents()
		self.addCleanup(dialog.close)
		return dialog

	def test_long_title_does_not_add_a_horizontal_scrollbar(self):
		dialog = self._dialog_with_long_items(1)
		self.assertFalse(dialog._items.horizontalScrollBar().isVisible())

	def test_title_is_shown_in_a_header_and_window_title_stays_accessible(self):
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, lambda _query: [], title='Go To'
		)
		dialog.show()
		self.app.processEvents()

		self.assertEqual('Go To', dialog._header.text())
		self.assertTrue(dialog._header.isVisible())
		self.assertEqual('Quicksearch', dialog.windowTitle())
		dialog.close()

	def test_header_is_hidden_and_accessible_window_title_is_unchanged_without_title(
		self
	):
		self.assertEqual('', self.dialog._header.text())
		self.assertFalse(self.dialog._header.isVisible())
		self.assertEqual('Quicksearch', self.dialog.windowTitle())

	def test_header_shows_a_two_line_title(self):
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, lambda _query: [], title='Pack\nfiles'
		)
		dialog.show()
		self.app.processEvents()

		self.assertEqual('Pack\nfiles', dialog._header.text())
		self.assertTrue(dialog._header.isVisible())
		dialog.close()

	def test_exit_key_returns_query_and_switch_command(self):
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, lambda _query: [],
			exit_keys={'Ctrl+P': 'go_to'}
		)
		dialog.show()
		QTest.keyClicks(dialog._query, 'abc')
		QTest.keyClick(dialog._query, Qt.Key_P, Qt.ControlModifier)
		self.app.processEvents()

		self.assertEqual(QuicksearchExit('abc', 'go_to'), dialog.get_result())
		self.assertFalse(dialog.isVisible())
		dialog.close()

	def test_exit_key_mapped_to_none_closes_without_result(self):
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, lambda _query: [],
			exit_keys={'Ctrl+Shift+P': None}
		)
		dialog.show()
		QTest.keyClick(
			dialog._query, Qt.Key_P, Qt.ControlModifier | Qt.ShiftModifier
		)
		self.app.processEvents()

		self.assertIsNone(dialog.get_result())
		self.assertFalse(dialog.isVisible())
		dialog.close()

	def test_exit_keys_do_not_intercept_plain_text(self):
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, lambda _query: [],
			exit_keys={'Ctrl+P': 'go_to'}
		)
		dialog.show()
		QTest.keyClick(dialog._query, Qt.Key_P)
		self.app.processEvents()

		self.assertEqual('p', dialog._query.text())
		self.assertTrue(dialog.isVisible())
		dialog.close()

	def test_ctrl_p_without_exit_keys_keeps_normal_result_shape(self):
		dialog = Quicksearch(self.parent, _StubApp(), _CSS, lambda _query: [])
		dialog.show()
		QTest.keyClicks(dialog._query, 'abc')
		QTest.keyClick(dialog._query, Qt.Key_P, Qt.ControlModifier)
		self.assertTrue(dialog.isVisible())
		QTest.keyClick(dialog._query, Qt.Key_Return)
		self.app.processEvents()

		self.assertEqual(('abc', None), dialog.get_result())
		dialog.close()

	def test_single_long_item_is_fully_visible(self):
		dialog = self._dialog_with_long_items(1)
		self.assertGreaterEqual(
			dialog._items.viewport().height(), dialog._items.sizeHintForRow(0)
		)

	def test_last_of_several_long_items_is_fully_visible(self):
		dialog = self._dialog_with_long_items(3)
		self.assertGreaterEqual(
			dialog._items.viewport().height(),
			3 * dialog._items.sizeHintForRow(0),
		)
		self.assertFalse(dialog._items.verticalScrollBar().isVisible())

	def test_long_title_row_fits_the_list_width(self):
		dialog = self._dialog_with_long_items(1)
		self.assertLessEqual(
			dialog._items.visualRect(dialog._items.model().index(0, 0)).width(),
			dialog._items.viewport().width(),
		)

	def test_shift_highlight_drops_hidden_chars_and_moves_visible_chars(self):
		self.assertEqual([2, 3], shift_highlight([0, 1, 10, 11], 9))
		self.assertEqual([3], shift_highlight([3], 0))

	def test_elide_title_left_leaves_a_fitting_title_unchanged(self):
		font = QFont()
		shown, removed = elide_title_left('short', font, 1000)
		self.assertEqual(('short', 0), (shown, removed))

	def test_elide_title_left_keeps_the_end_of_an_overlong_title(self):
		font = QFont()
		shown, removed = elide_title_left('a very long folder name', font, 130)
		self.assertTrue(shown.startswith('…'))
		self.assertTrue(shown.endswith('name'))
		self.assertGreater(removed, 0)

	def test_elide_title_left_accepts_a_fractional_width(self):
		font = QFont()
		shown, removed = elide_title_left('a very long folder name', font, 130.5)
		self.assertTrue(shown.startswith('…'))
		self.assertTrue(shown.endswith('name'))
		self.assertGreater(removed, 0)

	def test_resize_to_widens_and_keeps_the_dialog_centered(self):
		default_width = self.dialog.width()
		center = self.dialog.x() + default_width / 2
		self.dialog._resize_to(default_width + 200)
		self.assertEqual(default_width + 200, self.dialog.width())
		self.assertEqual(center, self.dialog.x() + self.dialog.width() / 2)

	def test_resize_to_can_shrink_back_to_default_after_widening(self):
		default_width = self.dialog.width()
		self.dialog._resize_to(default_width + 200)
		self.dialog._resize_to(default_width)
		self.assertEqual(default_width, self.dialog.width())

	def test_resize_to_does_not_shrink_below_default(self):
		default_width = self.dialog.width()
		self.dialog._resize_to(default_width - 100)
		self.assertEqual(default_width, self.dialog.width())

	def test_resize_to_caps_at_parent_width(self):
		self.dialog._resize_to(5000)
		self.assertEqual(self.parent.width(), self.dialog.width())

	def test_request_refresh_updates_items_for_current_query_and_keeps_selection(self):
		items = [QuicksearchItem('first'), QuicksearchItem('selected')]
		queries = []
		def get_items(query):
			queries.append(query)
			return items
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, get_items, query='current query'
		)
		dialog.show()
		dialog._items.setCurrentIndex(dialog._items.model().index(1, 0))
		items[:] = [QuicksearchItem('new'), QuicksearchItem('selected')]

		dialog.request_refresh()
		self.app.processEvents()

		self.assertEqual('current query', dialog._query.text())
		self.assertEqual('current query', queries[-1])
		self.assertEqual('selected', dialog._curr_items[
			dialog._items.currentIndex().row()
		].value)

	def test_request_refresh_selects_first_item_when_selected_value_disappears(self):
		items = [QuicksearchItem('selected')]
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS, lambda _query: items
		)
		dialog.show()
		dialog._items.setCurrentIndex(dialog._items.model().index(0, 0))
		items[:] = [QuicksearchItem('first'), QuicksearchItem('second')]

		dialog.request_refresh()
		self.app.processEvents()

		self.assertEqual('first', dialog._curr_items[
			dialog._items.currentIndex().row()
		].value)

	def test_request_refresh_from_thread_runs_get_items_on_gui_thread(self):
		threads = []
		dialog = Quicksearch(
			self.parent, _StubApp(), _CSS,
			lambda _query: threads.append(threading.get_ident()) or []
		)
		threads.clear()
		dialog.show()
		worker = threading.Thread(target=dialog.request_refresh)
		worker.start()
		worker.join()

		self.app.processEvents()

		self.assertEqual([threading.get_ident()], threads)

	def test_request_refresh_after_close_does_not_raise(self):
		self.dialog.show()
		self.dialog.close()

		self.dialog.request_refresh()
		self.app.processEvents()

	def test_dragging_right_grip_widens_by_twice_the_drag_distance(self):
		self.dialog.show()
		self.app.processEvents()
		start_width = self.dialog.width()
		grip = self.dialog._right_grip
		start = grip.rect().center()
		QTest.mousePress(grip, Qt.LeftButton, pos=start)
		self.assertIsNotNone(grip._start_x)
		move_to = start + QPoint(40, 0)
		global_x = grip._start_x + 40
		global_y = grip.mapToGlobal(start).y()
		global_pos = QPointF(global_x, global_y)
		QTest.mouseMove(grip, move_to)
		# Offscreen QtTest moves the cursor but may omit the held-button move.
		move_event = QMouseEvent(
			QEvent.MouseMove, QPointF(move_to), global_pos, Qt.NoButton,
			Qt.LeftButton, Qt.NoModifier
		)
		self.app.sendEvent(grip, move_event)
		self.assertEqual(start_width + 80, self.dialog.width())
		release_pos = grip.mapFromGlobal(QPoint(global_x, global_y))
		QTest.mouseRelease(grip, Qt.LeftButton, pos=release_pos)
		self.app.processEvents()
		self.assertEqual(start_width + 2 * 40, self.dialog.width())


class _StubApp:
	def exit(self, _code):
		pass
