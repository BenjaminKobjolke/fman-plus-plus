from fman.impl.model.shading import Shade, ShadeRole
from fman.impl.view.file_shading import paint_shaded
from fman.impl.view import FileListItemDelegate
from PyQt5.QtWidgets import QStyle, QStyleOptionViewItem
from unittest import TestCase


class _Index:
	def __init__(self, shade):
		self._shade = shade
	def data(self, role):
		return self._shade if role == ShadeRole else None
	def column(self):
		return 0
	def model(self):
		return _Model()


class _Model:
	def columnCount(self):
		return 1


class FileShadingTest(TestCase):
	def test_transparency_saves_and_restores_opacity(self):
		painter = _Painter()
		painted = []
		paint_shaded(
			lambda painter, option, index: painted.append('normal'),
			painter, QStyleOptionViewItem(), _Index(Shade('transparency', .5))
		)
		self.assertEqual([('save',), ('opacity', .7), ('restore',)], painter.calls)
		self.assertEqual(['normal'], painted)
	def test_selected_and_cursor_rows_paint_without_shading(self):
		for state in (QStyle.State_Selected, QStyle.State_HasFocus):
			option = QStyleOptionViewItem()
			option.state |= state
			painter = _Painter()
			painted = []
			paint_shaded(
				lambda painter, option, index: painted.append('normal'),
				painter, option, _Index(Shade('transparency', 1))
			)
			self.assertEqual([], painter.calls)
			self.assertEqual(['normal'], painted)
	def test_tint_paints_text_overlay_without_icon(self):
		painter = _Painter()
		options = []
		paint_shaded(
			lambda painter, option, index: options.append(option),
			painter, QStyleOptionViewItem(), _Index(Shade('tint', .25))
		)
		self.assertEqual(2, len(options))
		overlay = options[1]
		self.assertTrue(overlay.state & QStyle.State_On)
		self.assertFalse(overlay.features & QStyleOptionViewItem.HasDecoration)
		self.assertTrue(overlay.icon.isNull())
		self.assertEqual([
			('save',), ('opacity', .75), ('restore',)
		], painter.calls)
	def test_bold_style_bolds_recent_rows(self):
		option = QStyleOptionViewItem()
		FileListItemDelegate().adapt_style_option(
			option, _Index(Shade('bold', .49))
		)
		self.assertTrue(option.font.bold())
	def test_bold_style_leaves_older_rows_unchanged(self):
		option = QStyleOptionViewItem()
		FileListItemDelegate().adapt_style_option(
			option, _Index(Shade('bold', .5))
		)
		self.assertFalse(option.font.bold())


class _Painter:
	def __init__(self):
		self.calls = []
	def save(self):
		self.calls.append(('save',))
	def restore(self):
		self.calls.append(('restore',))
	def setOpacity(self, opacity):
		self.calls.append(('opacity', opacity))
