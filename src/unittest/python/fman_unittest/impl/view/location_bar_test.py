"""Location bar interaction tests use a QApplication of their own."""

from fman.impl.view.location_bar import LocationBar
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import patch


class LocationBarTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.bar = LocationBar()
		path = 'zip://root/parent/current'
		# Default Qt fonts vary by machine; size the fixture from the active font.
		self.bar.resize(
			self.bar.fontMetrics().horizontalAdvance(path) + 20, 30
		)
		self.bar.set_location(path)
		self.bar.show()
		self.app.processEvents()
		self.segment_clicks = []
		self.go_to_clicks = []
		self.bar.segment_clicked.connect(self.segment_clicks.append)
		self.bar.clicked.connect(lambda: self.go_to_clicks.append(True))
		self.addCleanup(self.bar.deleteLater)

	def test_clicking_parent_folder_emits_its_url(self):
		self._click_text('parent')

		self.assertEqual(['zip://root/parent'], self.segment_clicks)
		self.assertEqual([], self.go_to_clicks)

	def test_clicking_current_folder_opens_go_to(self):
		self._click_text('current')

		self.assertEqual([], self.segment_clicks)
		self.assertEqual([True], self.go_to_clicks)

	def test_clicking_space_after_path_opens_go_to(self):
		self._click(self.bar.width() - 4)

		self.assertEqual([], self.segment_clicks)
		self.assertEqual([True], self.go_to_clicks)

	def test_disabled_clickable_path_opens_go_to_for_parent(self):
		self.bar.set_clickable(False)

		self._click_text('parent')

		self.assertEqual([], self.segment_clicks)
		self.assertEqual([True], self.go_to_clicks)

	def test_hovering_parent_folder_shows_pointing_hand(self):
		self._move_to_text('parent')

		self.assertEqual(Qt.PointingHandCursor, self.bar.cursor().shape())

	def test_hovering_current_folder_restores_arrow_cursor(self):
		self._move_to_text('parent')
		self._move_to_text('current')

		self.assertEqual(Qt.ArrowCursor, self.bar.cursor().shape())

	def test_shortens_deep_paths_and_keeps_the_head_and_current_folder(self):
		self._use_deep_path()

		self.assertIn('…', self.bar.text())
		self.assertTrue(self.bar.text().startswith(r'C:\Users'))
		self.assertTrue(self.bar.text().endswith(r'\fman\src'))

	def test_tooltip_always_contains_the_full_human_readable_path(self):
		path = 'zip://root/parent/current'
		self.bar.set_location(path)

		self.assertEqual(path, self.bar.toolTip())

	def test_clicking_a_visible_parent_after_ellipsis_opens_it(self):
		self._use_deep_path()
		self._click_text('fman')

		self.assertEqual(
			['file://C:/Users/bob/Documents/Projects/fman'],
			self.segment_clicks,
		)
		self.assertEqual([], self.go_to_clicks)

	def test_clicking_ellipsis_shows_hidden_parent_menu_in_order(self):
		self._use_deep_path()
		shown_segments = []

		def show_menu(segments, _pos):
			shown_segments.extend(segments)
			self.bar.segment_clicked.emit(segments[-1].url)

		with patch.object(self.bar, '_show_hidden_menu', side_effect=show_menu):
			self._click_text('…')

		self.assertEqual(
			[
				'file://C:/Users/bob',
				'file://C:/Users/bob/Documents',
				'file://C:/Users/bob/Documents/Projects',
			],
			[segment.url for segment in shown_segments],
		)
		self.assertEqual(
			['file://C:/Users/bob/Documents/Projects'], self.segment_clicks
		)
		self.assertEqual([], self.go_to_clicks)

	def test_hidden_menu_emits_the_selected_folder(self):
		self._use_deep_path()
		segments = self.bar._hidden_segments(self.bar._shortened.hidden[0])
		menu_labels = []

		def choose_last_action(menu, *_args):
			menu_labels.extend(action.text() for action in menu.actions())
			return menu.actions()[-1]

		with patch(
			'fman.impl.view.location_bar.QMenu.exec_',
			new=choose_last_action,
		):
			self.bar._show_hidden_menu(segments, QPoint(0, self.bar.height()))

		self.assertEqual(['bob', 'Documents', 'Projects'], menu_labels)
		self.assertEqual(
			['file://C:/Users/bob/Documents/Projects'], self.segment_clicks
		)

	def test_resizing_recomputes_shortening_and_restores_full_path(self):
		self._use_deep_path()
		self.assertIn('…', self.bar.text())

		self.bar.resize(1000, 30)
		self.app.processEvents()

		self.assertEqual(self.bar.toolTip(), self.bar.text())

	def test_disabled_clickable_path_uses_go_to_for_ellipsis(self):
		self._use_deep_path()
		self.bar.set_clickable(False)
		self._click_text('…')

		self.assertEqual([], self.segment_clicks)
		self.assertEqual([True], self.go_to_clicks)

	def test_hovering_ellipsis_shows_pointing_hand(self):
		self._use_deep_path()
		self._move_to_text('…')

		self.assertEqual(Qt.PointingHandCursor, self.bar.cursor().shape())

	def _use_deep_path(self):
		self.bar.setMinimumWidth(0)
		path = 'file://C:/Users/bob/Documents/Projects/fman/src'
		self.bar.set_location(path)
		shortened_path = r'C:\Users\…\fman\src'
		self.bar.resize(
			self.bar.fontMetrics().horizontalAdvance(shortened_path) + 20,
			30,
		)

	def _click_text(self, text):
		self._click(self._text_position(text))

	def _move_to_text(self, text):
		self._send_mouse(QEvent.MouseMove, self._text_position(text), Qt.NoButton)

	def _text_position(self, text):
		index = self.bar.text().index(text) + len(text) // 2
		y = self.bar.height() // 2
		for x in range(self.bar.width()):
			if self.bar.cursorPositionAt(QPoint(x, y)) == index:
				return x
		self.fail('Text position is not visible in the location bar')

	def _click(self, x):
		self._send_mouse(QEvent.MouseButtonPress, x, Qt.LeftButton)

	def _send_mouse(self, event_type, x, button):
		pos = QPoint(x, self.bar.height() // 2)
		QApplication.sendEvent(self.bar, QMouseEvent(
			event_type, QPointF(pos), button,
			button if button != Qt.NoButton else Qt.NoButton,
			Qt.NoModifier
		))
