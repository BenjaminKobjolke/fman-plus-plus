from fman.impl.model.table import DimmedRole
from fman.impl.view import FileListItemDelegate
from PyQt5.QtWidgets import QStyle, QStyleOptionViewItem
from unittest import TestCase


class _Model:
	def columnCount(self):
		return 1


class _Index:
	def __init__(self, dimmed):
		self._dimmed = dimmed
	def column(self):
		return 0
	def model(self):
		return _Model()
	def data(self, role):
		return self._dimmed if role == DimmedRole else None


class DimmedRowsTest(TestCase):
	def test_dimmed_rows_clear_enabled_state_but_keep_cell_selectors(self):
		option = QStyleOptionViewItem()
		option.state |= QStyle.State_Enabled
		FileListItemDelegate().adapt_style_option(option, _Index(True))
		self.assertFalse(option.state & QStyle.State_Enabled)
		self.assertTrue(option.state & QStyle.State_Children)
		self.assertTrue(option.state & QStyle.State_Open)
	def test_normal_rows_keep_enabled_state(self):
		option = QStyleOptionViewItem()
		option.state |= QStyle.State_Enabled
		FileListItemDelegate().adapt_style_option(option, _Index(False))
		self.assertTrue(option.state & QStyle.State_Enabled)
