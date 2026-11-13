from fman.impl.model.coloring import ColorRole
from fman.impl.view.file_coloring import paint_colored
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication, QStyle, QStyleOptionViewItem
from unittest import TestCase
from unittest.mock import Mock, patch


class _Index:
	def __init__(self, color):
		self.color = color
	def data(self, role):
		return self.color if role == ColorRole else None


class _Painter:
	def __init__(self):
		self.calls = []
	def setPen(self, color):
		self.calls.append(('pen', QColor(color)))
	def drawText(self, rect, alignment, text):
		self.calls.append(('text', rect, alignment, text))


class FileColoringTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls._app = QApplication.instance() or QApplication([])

	def test_uncolored_selected_focused_and_overlay_rows_use_plain_paint(self):
		for color, state in (
			(None, QStyle.State_None),
			(QColor('red'), QStyle.State_Selected),
			(QColor('red'), QStyle.State_HasFocus),
			(QColor('red'), QStyle.State_On),
		):
			option = QStyleOptionViewItem()
			option.state |= state
			plain = Mock()
			paint_colored(Mock(), plain, _Painter(), option, _Index(color))
			plain.assert_called_once()

	def test_colored_row_draws_empty_standard_item_then_colored_text(self):
		delegate = Mock()
		delegate.initStyleOption.side_effect = lambda option, index: setattr(
			option, 'text', 'photo.png'
		)
		style = Mock()
		style.subElementRect.return_value = QRect(2, 3, 80, 20)
		style.pixelMetric.return_value = 0
		option = QStyleOptionViewItem()
		option.rect = QRect(0, 0, 100, 24)
		painter = _Painter()

		with patch(
			'fman.impl.view.file_coloring.QApplication.style', return_value=style
		), \
			patch('fman.impl.view.file_coloring.QFontMetrics') as metrics:
			metrics.return_value.elidedText.return_value = 'photo.png'
			paint_colored(delegate, Mock(), painter, option, _Index(QColor('#123456')))

		drawn_option = style.drawControl.call_args.args[1]
		self.assertEqual('', drawn_option.text)
		self.assertEqual('#123456', painter.calls[0][1].name())
		self.assertEqual('photo.png', painter.calls[1][3])

	def test_hidden_row_scales_text_alpha(self):
		delegate = Mock()
		delegate.initStyleOption.side_effect = lambda option, index: setattr(
			option, 'text', 'hidden.png'
		)
		style = Mock()
		style.subElementRect.return_value = QRect(0, 0, 80, 20)
		style.pixelMetric.return_value = 0
		option = QStyleOptionViewItem()
		option.state &= ~QStyle.State_Enabled
		painter = _Painter()

		with patch(
			'fman.impl.view.file_coloring.QApplication.style', return_value=style
		), \
			patch('fman.impl.view.file_coloring.QFontMetrics') as metrics:
			metrics.return_value.elidedText.return_value = 'hidden.png'
			paint_colored(delegate, Mock(), painter, option, _Index(QColor(255, 0, 0)))

		self.assertEqual(round(255 * .6), painter.calls[0][1].alpha())
