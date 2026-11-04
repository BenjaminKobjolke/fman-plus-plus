"""Run via tools\\run_view_tests.bat; this suite owns a QApplication."""

from fman.impl.view import FileListView
from fman.impl.view.pane_view_mode import PaneViewMode
from fman_unittest.impl.view.compact_view_test import StubPaneModel
from PyQt5.QtCore import QSize
from unittest.mock import Mock
from PyQt5.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget
from unittest import TestCase


class PaneViewModeTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.pane = QWidget()
		self.layout = QVBoxLayout(self.pane)
		self.file_view = FileListView(self.pane, lambda *_: [])
		self.pane._location_bar = QLineEdit(self.pane)
		self.model = StubPaneModel(['alpha', 'beta'])
		self.file_view.setModel(self.model)
		self.layout.addWidget(self.file_view)
		self.pane.setFocusProxy(self.file_view)
		self.mode = PaneViewMode(self.pane, self.file_view)
		self.addCleanup(self.pane.deleteLater)

	def test_set_compact_swaps_visible_view_and_focus_proxy(self):
		self.mode.set_compact(True)
		compact_view = self.mode.visible_view()
		self.assertIsNot(compact_view, self.file_view)
		self.assertFalse(compact_view.isHidden())
		self.assertTrue(self.file_view.isHidden())
		self.assertIs(self.pane.focusProxy(), compact_view)
		self.assertIs(self.pane._location_bar.focusProxy(), compact_view)

		self.mode.set_compact(False)
		self.assertTrue(compact_view.isHidden())
		self.assertIs(self.pane.focusProxy(), self.file_view)
		self.assertIs(self.pane._location_bar.focusProxy(), self.file_view)

	def test_hide_and_restore_use_the_active_compact_view(self):
		self.mode.set_compact(True)
		compact_view = self.mode.visible_view()
		self.mode.hide()
		self.assertTrue(compact_view.isHidden())
		self.mode.restore()
		self.assertFalse(compact_view.isHidden())
		self.assertTrue(self.file_view.isHidden())

	def test_updates_reach_both_views_and_future_compact_view(self):
		self.mode.set_icon_size(24)
		self.mode.set_style_sheet('QWidget { color: red; }')
		self.mode.set_compact(True)
		compact_view = self.mode.visible_view()
		self.assertEqual(QSize(24, 24), compact_view.iconSize())
		self.assertIn('color: red', compact_view.styleSheet())
		self.assertEqual(QSize(24, 24), self.file_view.iconSize())
		self.assertIn('color: red', self.file_view.styleSheet())

	def test_double_click_is_forwarded_to_pane_callback(self):
		callback = Mock()
		mode = PaneViewMode(self.pane, self.file_view,
						on_doubleclicked=callback)
		mode.set_compact(True)
		index = self.model.index(0, 0)
		mode.visible_view().doubleClicked.emit(index)
		callback.assert_called_once_with(index)
