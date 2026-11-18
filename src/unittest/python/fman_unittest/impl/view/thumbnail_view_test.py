"""Run via tools\\run_view_tests.bat; this suite owns a QApplication."""

from fman.impl.view import FileListView
from fman.impl.view.thumbnail_settings import ThumbnailSettings
from fman.impl.view.thumbnail_view import ThumbnailFileView
from fman_unittest.impl.view.compact_view_test import StubPaneModel
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QColor, QImage, QKeyEvent, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QStyleOptionViewItem
from PyQt5.QtCore import QRect
from fman.impl.view.thumbnail_delegate import ThumbnailDelegate
from unittest import TestCase
from unittest.mock import Mock


class ThumbnailViewTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.model = StubPaneModel(['one.png', 'two.png', 'three.png'])
		self.file_view = FileListView(None, lambda *_: [])
		self.file_view.setModel(self.model)
		self.file_view.request_rows = Mock()
		self.file_view.key_press_event_filter = Mock(return_value=True)
		self.cache = Mock()
		self.cache._settings = ThumbnailSettings()
		self.cache.get.return_value = None
		self.view = ThumbnailFileView(self.file_view, self.cache)
		self.view.resize(320, 240)
		self.view.setModel(self.model)
		self.view.setSelectionModel(self.file_view.selectionModel())
		self.view.set_thumbnail_settings(ThumbnailSettings(size=100))
		self.view.show()
		self.app.processEvents()
		self.addCleanup(self.view.deleteLater)
		self.addCleanup(self.file_view.deleteLater)

	def test_settings_set_icon_grid_and_wrapped_labels(self):
		self.assertEqual(self.view.viewMode(), self.view.IconMode)
		self.assertEqual(self.view.flow(), self.view.LeftToRight)
		self.assertTrue(self.view.isWrapping())
		self.assertEqual(self.view.verticalScrollBarPolicy(), Qt.ScrollBarAsNeeded)
		self.assertEqual(self.view.gridSize().width(), 124)
		self.assertEqual(
			self.view.gridSize().height(),
			100 + self.view.fontMetrics().height() * 2 + 12,
		)
		self.assertTrue(self.view.wordWrap())

	def test_model_and_selection_model_are_shared(self):
		self.assertIs(self.view.model(), self.file_view.model())
		self.assertIs(self.view.selectionModel(), self.file_view.selectionModel())
		self.file_view.select(['stub://two.png'])
		self.assertTrue(self.view.selectionModel().isSelected(self.model.index(1, 0)))

	def test_context_menu_is_forwarded_to_file_view(self):
		event = Mock()
		self.file_view.show_context_menu = Mock()
		index = self.model.index(0, 0)
		self.view._show_context_menu_for(event, index)
		args = self.file_view.show_context_menu.call_args.args
		self.assertIs(args[0], event)
		self.assertEqual(args[1], index)
		self.assertEqual(args[2], 0)

	def test_key_filter_is_shared(self):
		event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Left, Qt.NoModifier)
		self.view.keyPressEvent(event)
		self.file_view.key_press_event_filter.assert_called_once_with(event)

	def test_paint_requests_preview_urls_for_visible_rows(self):
		self.view._request_visible_rows()
		requested = self.cache.request.call_args.args[0]
		self.assertTrue(requested)
		self.assertTrue(all(url.startswith('stub://') for url in requested))

	def test_paint_requests_preview_for_item_centred_in_wide_cell(self):
		self.view.setModel(StubPaneModel(['a.jpg']))
		self.view.set_thumbnail_settings(ThumbnailSettings(size=128))
		self.view.resize(400, 300)
		self.app.processEvents()
		self.view.setGridSize(QSize(
			128 + self.view.GRID_PADDING,
			128 + self.view.fontMetrics().height() * 2 + 12,
		))
		self.cache.request.reset_mock()

		self.view._request_visible_rows()

		self.cache.request.assert_called_once_with(['stub://a.jpg'])

	def test_request_finds_rows_when_items_are_smaller_than_the_grid_cell(self):
		self.view.set_thumbnail_settings(ThumbnailSettings(size=200))
		self.view.resize(80, 100)
		self.app.processEvents()
		self.assertFalse(self.view.indexAt(QPoint(1, 1)).isValid())
		self.cache.request.reset_mock()
		self.file_view.request_rows.reset_mock()

		self.view._request_visible_rows()

		self.cache.request.assert_called_once_with(['stub://one.png'])
		self.file_view.request_rows.assert_called_once_with([0])

	def test_request_covers_rows_after_scrolling(self):
		model = StubPaneModel([f'{row}.png' for row in range(30)])
		self.view.setModel(model)
		self.file_view.setModel(model)
		self.view.setSelectionModel(self.file_view.selectionModel())
		self.view.scrollToBottom()
		self.app.processEvents()
		self.cache.request.reset_mock()
		self.file_view.request_rows.reset_mock()

		self.view._request_visible_rows()

		self.cache.request.assert_called_once()
		requested_urls = self.cache.request.call_args.args[0]
		self.assertIn('stub://29.png', requested_urls)
		self.assertNotIn('stub://0.png', requested_urls)

	def test_model_changes_keep_thumbnail_grid(self):
		self.view.setModel(StubPaneModel(['a.jpg']))
		self.view.set_thumbnail_settings(ThumbnailSettings(size=128))

		self.view.set_grid_width()

		self.assertEqual(
			self.view.gridSize(),
			QSize(
				128 + self.view.GRID_PADDING,
				128 + self.view.fontMetrics().height() * 2 + 12,
			),
		)

	def test_delegate_paints_cached_preview_over_the_file_icon(self):
		image = QImage(80, 100, QImage.Format_ARGB32)
		image.fill(QColor('black'))
		painter = QPainter(image)
		base_delegate = Mock()
		base_delegate.paint.side_effect = lambda painter, option, index: \
			painter.fillRect(QRect(25, 5, 30, 30), QColor('green'))
		preview = QPixmap(30, 30)
		preview.fill(QColor('red'))
		self.cache.get.return_value = preview
		index = Mock()
		index.model.return_value.url.return_value = 'stub://one.png'
		delegate = ThumbnailDelegate(self.view, self.cache, base_delegate)
		option = QStyleOptionViewItem()
		option.rect = QRect(0, 0, 80, 100)

		delegate.paint(painter, option, index)
		painter.end()

		self.assertEqual(QColor('red'), image.pixelColor(30, 10))
