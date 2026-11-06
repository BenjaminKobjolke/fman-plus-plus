"""Context menu for showing and hiding file list columns."""
from core.column_visibility import is_column_hidden
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.view import Menu
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction

@run_in_main_thread
def install_header_menu(pane, toggle):
	header = pane._widget._file_view.horizontalHeader()
	header.setContextMenuPolicy(Qt.CustomContextMenu)
	def show_menu(pos):
		menu = Menu(header)
		for name in pane.get_columns()[1:]:
			action = QAction(name.rsplit('.', 1)[-1], menu)
			action.setCheckable(True)
			action.setChecked(not is_column_hidden(name))
			action.triggered.connect(lambda _checked=False, column=name: toggle(column))
			menu.addAction(action)
		menu.exec_(header.mapToGlobal(pos))
	header.customContextMenuRequested.connect(show_menu)
