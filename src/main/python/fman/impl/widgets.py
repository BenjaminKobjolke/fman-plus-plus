from fbs_runtime.platform import is_windows, is_mac
from fman import APP_NAME, OK
from fman.impl.background import chrome_is_transparent, for_window
from fman.impl.frameless_dialog import make_frameless
from fman.impl.model import SortedFileSystemModel
from fman.impl.quicksearch import Quicksearch
from fman.impl.util.qt import disable_window_animations_mac, Key_Escape, \
	NoFocus, Key_Backspace, DisplayRole
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.view.backgrounds import PAINTER, set_transparent
from fman.impl.view.location_bar import LocationBar
from fman.impl.view import FileListView, Layout, set_selection
from fman.impl.workers_label import WorkersLabel
from fman.url import as_human_readable, basename, splitscheme
from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QEvent, QSize, QPoint, \
	QRect
from PyQt5.QtGui import QKeySequence, QPainter
from PyQt5.QtWidgets import QWidget, QMainWindow, QSplitter, QStatusBar, \
	QMessageBox, QInputDialog, QLineEdit, QFileDialog, QLabel, QDialog, \
	QHBoxLayout, QPushButton, QVBoxLayout, QSplitterHandle, QApplication, \
	QFrame, QAction, QSizePolicy, QProgressDialog, QProgressBar, \
	QDialogButtonBox, QSpacerItem
from collections import namedtuple
from time import time

import re

class Application(QApplication):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._main_window = None
		self.applicationStateChanged.connect(self._on_state_changed)
	def set_main_window(self, main_window):
		self._main_window = main_window
		# Ensure all other windows are closed as well when the main window
		# is closed. (This in particular closes windows opened by plugins.)
		main_window.closed.connect(self.quit)
	@run_in_main_thread
	def exit(self, returnCode=0):
		if self._main_window is not None:
			self._main_window.close()
		super().exit(returnCode)
	@run_in_main_thread
	def set_style_sheet(self, stylesheet):
		self.setStyleSheet(stylesheet)
	def _on_state_changed(self, new_state):
		if new_state == Qt.ApplicationActive:
			for pane in self._main_window.get_panes():
				pane.reload()

NETWORK_SCHEME = 'network://'
# `detail` is formatted with the elapsed seconds. The ticking number is the
# point: a message that never changes on an empty pane reads as a frozen app.
LoadingMessage = namedtuple('LoadingMessage', ('title', 'detail'))
LOADING_MESSAGE = LoadingMessage(
	'Loading…', 'Still reading this folder (%d s).'
)
LOADING_MESSAGE_NETWORK = LoadingMessage(
	'Searching network shares…',
	'Waiting for Windows to return the network browse list (%d s).\n'
	'A machine that is switched off or unreachable can hold this up.'
)
# Only show the indicator once a listing is visibly slow - without this, every
# local directory would flash it. Doubles as the redraw interval, so the
# elapsed seconds stay current.
LOADING_INDICATOR_DELAY_MS = 400

def format_loading_message(message, elapsed_secs):
	return '%s\n\n%s' % (message.title, message.detail % elapsed_secs)

class DirectoryPaneWidget(QWidget):

	location_changed = pyqtSignal(QWidget)
	location_bar_clicked = pyqtSignal(QWidget)

	def __init__(self, fs, null_location, parent, controller):
		super().__init__(parent)
		self._location_bar = LocationBar(self)
		self._model = SortedFileSystemModel(self, fs, null_location)
		self._model.file_renamed.connect(self._on_file_renamed)
		self._model.files_dropped.connect(self._on_files_dropped)
		self._file_view = FileListView(
			self, lambda *args: controller.on_context_menu(self, *args)
		)
		self._file_view.setModel(self._model)
		self._file_view.doubleClicked.connect(self._on_doubleclicked)
		self._file_view.key_press_event_filter = self._on_key_pressed
		self.setLayout(Layout(self._location_bar, self._file_view))
		self._location_bar.setFocusProxy(self._file_view)
		self.setFocusProxy(self._file_view)
		# The widget currently shown in place of the file list - a file
		# viewer, or whatever a plugin mounted. See impl/view/pane_mount.py.
		self._mounted_widget = None
		self._controller = controller
		self._model.location_changed.connect(self._on_location_changed)
		self._model.location_loaded.connect(self._on_location_loaded)
		self._location_bar.clicked.connect(
			lambda: self.location_bar_clicked.emit(self)
		)
		self._filter_bar = FilterBar(self, self._model, self._file_view)
		self._loading_message = LOADING_MESSAGE
		self._loading_started = 0.0
		self._loading_timer = QTimer(self)
		self._loading_timer.setInterval(LOADING_INDICATOR_DELAY_MS)
		self._loading_timer.timeout.connect(self._on_loading_timeout)
	def set_icon_size(self, size):
		# An invalid QSize is how Qt is told to go back to its own
		# decorationSize, so size=None reads as "fman never asked".
		self._file_view.setIconSize(
			QSize() if size is None else QSize(size, size)
		)
	def set_backgrounds(self, backgrounds, pane_index):
		# The seam the window talks to: nothing outside this class
		# reaches into _file_view. The location bar is chrome like the
		# column header and the status bar, so it clears the same way.
		self._file_view.set_backgrounds(backgrounds, pane_index)
		set_transparent(self._location_bar, chrome_is_transparent(backgrounds))
	def resizeEvent(self, e):
		super().resizeEvent(e)
		self._filter_bar.reposition()
	@run_in_main_thread
	def move_cursor_up(self, toggle_selection=False):
		self._file_view.move_cursor_up(toggle_selection)
	@run_in_main_thread
	def move_cursor_down(self, toggle_selection=False):
		self._file_view.move_cursor_down(toggle_selection)
	@run_in_main_thread
	def move_cursor_home(self, toggle_selection=False):
		self._file_view.move_cursor_home(toggle_selection)
	@run_in_main_thread
	def move_cursor_end(self, toggle_selection=False):
		self._file_view.move_cursor_end(toggle_selection)
	@run_in_main_thread
	def move_cursor_page_up(self, toggle_selection=False):
		self._file_view.move_cursor_page_up(toggle_selection)
	@run_in_main_thread
	def move_cursor_page_down(self, toggle_selection=False):
		self._file_view.move_cursor_page_down(toggle_selection)
	@run_in_main_thread
	def focus(self):
		self.setFocus()
	@run_in_main_thread
	def select_all(self):
		self._file_view.selectAll()
	@run_in_main_thread
	def clear_selection(self):
		self._file_view.clearSelection()
	@run_in_main_thread
	def toggle_selection(self, file_url):
		self._file_view.toggle_selection(file_url)
	@run_in_main_thread
	def select(self, file_urls, ignore_errors=False):
		self._file_view.select(file_urls, ignore_errors)
	@run_in_main_thread
	def deselect(self, file_urls, ignore_errors=False):
		self._file_view.deselect(file_urls, ignore_errors)
	@run_in_main_thread
	def get_selected_files(self):
		return self._file_view.get_selected_files()
	@run_in_main_thread
	def get_file_under_cursor(self):
		return self._file_view.get_file_under_cursor()
	@run_in_main_thread
	def get_location(self):
		return self._model.get_location()
	def set_location(
		self, url, sort_column='', ascending=True, callback=None, onerror=None
	):
		self._model.set_location(url, sort_column, ascending, callback, onerror)
	def reload(self):
		self._model.reload()
	@run_in_main_thread
	def place_cursor_at(self, file_url):
		self._file_view.place_cursor_at(file_url)
	@run_in_main_thread
	def edit_name(self, file_url, selection_start=0, selection_end=None):
		self._file_view.edit_name(file_url, selection_start, selection_end)
	@run_in_main_thread
	def add_filter(self, filter_):
		self._model.add_filter(filter_)
	@run_in_main_thread
	def remove_filter(self, filter_):
		self._model.remove_filter(filter_)
	@property
	def window(self):
		return self.parentWidget().parentWidget()
	def get_columns(self):
		return [
			column.get_qualified_name() for column in self._model.get_columns()
		]
	@run_in_main_thread
	def set_sort_column(self, column, ascending=True):
		column_index = self.get_columns().index(column)
		order = Qt.AscendingOrder if ascending else Qt.DescendingOrder
		self._file_view.sortByColumn(column_index, order)
	@run_in_main_thread
	def get_sort_column(self):
		header = self._file_view.horizontalHeader()
		column_index = header.sortIndicatorSection()
		column = self.get_columns()[column_index]
		ascending = header.sortIndicatorOrder() == Qt.AscendingOrder
		return column, ascending
	@run_in_main_thread
	def get_column_widths(self):
		return [self._file_view.columnWidth(i) for i in (0, 1)]
	@run_in_main_thread
	def set_column_widths(self, column_widths):
		num_columns = self._model.columnCount()
		if len(column_widths) != num_columns:
			raise ValueError(
				'Wrong number of columns: len(%r) != %d'
				% (column_widths, num_columns)
			)
		for i, width in enumerate(column_widths):
			self._file_view.setColumnWidth(i, width)
	def _on_doubleclicked(self, index):
		self._controller.on_doubleclicked(self, self._model.url(index))
	def _on_key_pressed(self, event):
		if self._filter_bar.isVisible() and event.key() == Key_Backspace:
			self._filter_bar.handle_keypress(event)
			return True
		if self._controller.handle_shortcut(self, event):
			return True
		if self._filter_bar.handle_keypress(event):
			return True
		if self._controller.handle_nonexistent_shortcut(self, event):
			return True
		event.ignore()
		return False
	def _on_file_renamed(self, *args):
		self._controller.on_file_renamed(self, *args)
	def _on_files_dropped(self, *args):
		self._controller.on_files_dropped(self, *args)
	def _on_location_changed(self, url):
		self._filter_bar.close()
		self._location_bar.setText(as_human_readable(url))
		if splitscheme(url)[0] == NETWORK_SCHEME:
			self._loading_message = LOADING_MESSAGE_NETWORK
		else:
			self._loading_message = LOADING_MESSAGE
		self._loading_started = time()
		self._loading_timer.start()
	def _on_loading_timeout(self):
		self._file_view.set_loading(format_loading_message(
			self._loading_message, time() - self._loading_started
		))
	def _on_location_loaded(self, url):
		self._loading_timer.stop()
		self._file_view.set_loading('')
		if not self.get_file_under_cursor():
			self.move_cursor_home()
		self._file_view.resizeColumnsToContents()
		self.location_changed.emit(self)

class FilterBar(QFrame):
	def __init__(self, parent, model, file_view):
		super().__init__(parent)
		self._model = model
		self._file_view = file_view
		self.setVisible(False)
		self._input = QLineEdit()
		self._input.textChanged.connect(self._on_text_changed)
		self.setFrameShape(QFrame.Box)
		self.setFrameShadow(QFrame.Raised)
		layout = QVBoxLayout()
		layout.addWidget(self._input)
		layout.setContentsMargins(0, 0, 0, 0)
		self.setLayout(layout)
		self.setFocusPolicy(NoFocus)
		self._input.setFocusPolicy(NoFocus)
		self._filter_re = re.compile('', re.I)
		self._model.add_filter(self._accepts)
		file_view.verticalScrollBar().rangeChanged.connect(
			self._on_scroll_range_changed
		)
	def handle_keypress(self, event):
		if event.key() == Key_Escape:
			self.close()
			return True
		query_before = self._input.text()
		self._input.keyPressEvent(event)
		query = self._input.text()
		result = query != query_before
		# Prevent Arrow-Left/-Right from changing the cursor position:
		self._input.setCursorPosition(len(query))
		self.setVisible(bool(query))
		if result:
			self._select_row_with_prefix(query)
		return result
	def _select_row_with_prefix(self, query):
		query_lower = query.lower()
		m = self._model
		def has_required_prefix(index):
			return m.data(index, DisplayRole).lower().startswith(query_lower)
		curr = self._file_view.currentIndex()
		if curr.isValid() and has_required_prefix(curr):
			# We're already at a row with the required prefix. Nothing to do.
			return
		for i in range(m.rowCount()):
			idx = m.index(i, 0)
			if has_required_prefix(idx):
				self._file_view.setCurrentIndex(idx)
				break
	def close(self):
		self.hide()
		self._input.setText('')
	def reposition(self, scroll_bar_visible=None):
		padding = QSize(5, 5)
		pos = self.parent().size() - self.size() - padding
		scroll_bar = self._file_view.verticalScrollBar()
		if scroll_bar_visible is None:
			scroll_bar_visible = scroll_bar.isVisible()
		if scroll_bar_visible:
			pos -= QSize(scroll_bar.width(), 0)
		self.move(pos.width(), pos.height())
	def _on_scroll_range_changed(self, min_, max_):
		self.reposition(scroll_bar_visible=min_ or max_)
	def _on_text_changed(self, text):
		text_re = '.*'.join(map(re.escape, text.split('*')))
		self._filter_re = re.compile(text_re, re.I)
		self._model.sourceModel().update()
	def _accepts(self, url):
		return bool(self._filter_re.search(basename(url)))

OVERLAY_MARGIN = 20

def _overlay_pos(
	window_size, overlay_size, bottom_inset, dialog_rect=None,
	margin=OVERLAY_MARGIN
):
	"""
	Where to put an overlay: hugging the bottom right corner, `bottom_inset`
	pixels (the status bar, when it is shown) above the window's bottom edge.

	The tutorial's overlay used to be centered - right on top of the file list
	it was asking the user to navigate. Down here it is clear of the rows.

	`dialog_rect` is where an open dialog sits in the window, if any. The
	overlay only moves out of its way - to just above the dialog - when the two
	would actually overlap, so that opening the command palette does not make
	the overlay jump for no reason.
	"""
	x = max(window_size.width() - overlay_size.width() - margin, 0)
	y = window_size.height() - overlay_size.height() - bottom_inset - margin
	if dialog_rect is not None \
		and dialog_rect.intersects(QRect(QPoint(x, max(y, 0)), overlay_size)):
		# Raising the overlay would not help: dialogs are windows of their own.
		# Above the dialog, not merely at the top margin: the command palette is
		# centered and tall, so it covers the top right corner as well - which
		# is where the tutorial's bubble used to land on top of it.
		y = dialog_rect.top() - overlay_size.height() - margin
	# Clamping to 0 keeps the overlay's title and the beginning of its text on
	# screen - when it is taller than the window, and when a dialog leaves no
	# room above it either. The latter still overlaps; there is nowhere to go.
	return QPoint(x, max(y, 0))

class MainWindow(QMainWindow):

	shown = pyqtSignal()
	closed = pyqtSignal()
	before_dialog = pyqtSignal(QDialog)

	def __init__(
		self, app, help_menu_actions, theme, progress_bar_palette, fs,
		null_location
	):
		super().__init__()
		self._controller = None
		self._app = app
		self._theme = theme
		self._progress_bar_palette = progress_bar_palette
		self._fs = fs
		self._null_location = null_location
		self._panes = []
		self._file_list_icon_size = None
		self._backgrounds = ()
		self._splitter = Splitter(self)
		self.setCentralWidget(self._splitter)
		self._status_bar = QStatusBar(self)
		self._status_bar_text = QLabel(self._status_bar)
		# QLabel's minimum width follows its text, which can stop the window narrowing.
		self._status_bar_text.setMinimumWidth(1)
		self._status_bar_text.setOpenExternalLinks(True)
		self._status_bar.addWidget(self._status_bar_text)
		self._status_bar.setSizeGripEnabled(False)
		self.setStatusBar(self._status_bar)
		self._timer = QTimer(self)
		self._timer.timeout.connect(self.clear_status_message)
		self._timer.setSingleShot(True)
		self._dialog = None
		self._help_menu = None
		self._framed_geometry = None
		self._init_help_menu(help_menu_actions)
	def set_controller(self, controller):
		self._controller = controller
	def set_progress_bar_palette(self, palette):
		# Each ProgressDialog reads this when it is created, so switching
		# theme (fman.impl.themes) recolors the next one without a restart.
		self._progress_bar_palette = palette
	def set_file_list_icon_size(self, size):
		# Remembered as well as applied: add_pane hands it to panes opened
		# after the switch, which would otherwise stay at Qt's default.
		# size=None means "don't touch it" - see themes.DEFAULT_ICON_SIZE.
		self._file_list_icon_size = size
		for pane in self._panes:
			pane.set_icon_size(size)
	@run_in_main_thread
	def set_backgrounds(self, backgrounds):
		# Remembered as well as applied, for the same reason as the icon
		# size above - and for one more: at startup this runs before the
		# session has opened a single pane.
		self._backgrounds = backgrounds
		set_transparent(self._status_bar, chrome_is_transparent(backgrounds))
		for index, pane in enumerate(self._panes):
			pane.set_backgrounds(backgrounds, index)
		self.update()
	def paintEvent(self, event):
		super().paintEvent(event)
		backgrounds = for_window(self._backgrounds)
		if backgrounds:
			# Over QMainWindow's own fill but under its children, which
			# is where a background belongs. The panes, the header and
			# the status bar only let it through once set_transparent
			# has switched their opaque backgrounds off.
			PAINTER.paint(QPainter(self), self.rect(), backgrounds)
	def _init_help_menu(self, help_menu_actions):
		if not help_menu_actions:
			return
		help_menu_text = 'Help'
		if is_mac():
				# On OS X, any menu named "Help" has the "Spotlight search for
				# Help" bar displayed in it. We don't need or want this. Add an
				# invisible character to fool OS X into not treating it as
				# "Help" (' ' doesn't work):
				help_menu_text += '\u2063'
		help_menu = self._help_menu = self.menuBar().addMenu(help_menu_text)
		actions = []
		for action_name, shortcut, handler in help_menu_actions:
			action = QAction(action_name, help_menu)
			action.triggered.connect(handler)
			help_menu.addAction(action)
			actions.append(action)
		# On at least Mac, pressing a shortcut from a menu briefly highlights
		# the menu. We don't want this - especially for the Command Palette.
		# We therefore only enable the shortcuts when the menu is open:
		def enable_shortcuts():
			for i, (_, shortcut, _) in enumerate(help_menu_actions):
				if shortcut:
					actions[i].setShortcut(QKeySequence(shortcut))
		help_menu.aboutToShow.connect(enable_shortcuts)
		def disable_shortcuts():
			for action in actions:
				action.setShortcut(QKeySequence())
		help_menu.aboutToHide.connect(disable_shortcuts)
	@run_in_main_thread
	def show_alert(
		self, text, buttons=OK, default_button=OK, allow_escape=True
	):
		alert = MessageBox(self, allow_escape)
		# API users might pass arbitrary objects as text when trying to
		# debug, eg. exception instances. Convert to str(...) to allow for
		# this:
		alert.setText(str(text))
		alert.setStandardButtons(buttons)
		alert.setDefaultButton(default_button)
		return self.exec_dialog(alert)
	@run_in_main_thread
	def show_file_open_dialog(self, caption, dir_path, filter_text):
		# Let API users pass arbitrary objects by converting with str(...):
		return QFileDialog.getOpenFileName(
			self, str(caption), str(dir_path), str(filter_text)
		)[0]
	@run_in_main_thread
	def show_prompt(
		self, text, default='', selection_start=0, selection_end=None
	):
		# Let API users pass arbitrary objects by converting str(text):
		text_str = str(text)
		dialog = Prompt(
			self, APP_NAME, text_str, default, selection_start, selection_end
		)
		dialog.setTextValue(default)
		result = self.exec_dialog(dialog)
		if result:
			return dialog.textValue(), True
		return '', False
	@run_in_main_thread
	def show_quicksearch(
		self, get_items, get_tab_completion=None, query='', item=0,
		alt_accept=False
	):
		css = self._theme.get_quicksearch_item_css()
		dialog = Quicksearch(
			self, self._app, css, get_items, get_tab_completion, query, item,
			alt_accept
		)
		result = self.exec_dialog(dialog)
		return result
	def _match_title_bar(self, dialog):
		# Dialogs that are always frameless, e.g. Quicksearch, keep their look.
		if not self.is_title_bar_visible() and \
				not dialog.windowFlags() & Qt.FramelessWindowHint:
			make_frameless(dialog)
	@run_in_main_thread
	def create_progress_dialog(self, title, task_size):
		dialog = ProgressDialog(
			self, title, task_size, self._progress_bar_palette
		)
		self._match_title_bar(dialog)
		return dialog
	@run_in_main_thread
	def exec_dialog(self, dialog):
		self._dialog = dialog
		self.before_dialog.emit(dialog)
		dialog.moveToThread(self._app.thread())
		dialog.setParent(self)
		self._match_title_bar(dialog)
		# No setWindowOpacity here on purpose: dialogs are top-level windows
		# of their own (Quicksearch is a QDialog; FramelessWindowHint is only
		# a hint), so the main window's opacity does not reach them and they
		# stay fully opaque - which is what keeps the command palette, prompts
		# and progress dialogs readable over a faded window.
		if is_mac():
			disable_window_animations_mac(dialog)
		# ProgressDialog is excluded: a copy can run for minutes, and dimming
		# the window for that long is worse than the contrast it buys.
		scrim = None if isinstance(dialog, ProgressDialog) else Scrim(self)
		if scrim:
			scrim.show()
		try:
			result = dialog.exec()
		finally:
			if scrim:
				scrim.close()
		self._dialog = None
		return result
	@run_in_main_thread
	def show_status_message(self, text, timeout_secs=None):
		self._status_bar_text.setText(text)
		if timeout_secs:
			self._timer.start(int(timeout_secs * 1000))
		else:
			self._timer.stop()
	@run_in_main_thread
	def clear_status_message(self):
		self.show_status_message('Ready.')
	@run_in_main_thread
	def add_pane(self):
		result = DirectoryPaneWidget(
			self._fs, self._null_location, self._splitter, self._controller
		)
		result.set_icon_size(self._file_list_icon_size)
		self._panes.append(result)
		# After the append, because the pane's own index is what decides
		# which of the theme's images belong to it.
		result.set_backgrounds(self._backgrounds, len(self._panes) - 1)
		self._splitter.addWidget(result)
		return result
	def get_panes(self):
		return self._panes
	@run_in_main_thread
	def remove_pane(self, pane_widget):
		self._panes.remove(pane_widget)
		pane_widget.setParent(None)
		pane_widget.deleteLater()
		for index, pane in enumerate(self._panes):
			pane.set_backgrounds(self._backgrounds, index)
		self.update()
	@run_in_main_thread
	def minimize(self):
		self.setWindowState(Qt.WindowMinimized)
	@run_in_main_thread
	def center_on_screen(self):
		# The screen the window is on, not the primary one: on two monitors,
		# "center" that teleports the window to the other screen is not what
		# anyone means. frameGeometry, not geometry, because the title bar and
		# border are part of what the user sees as the window;
		# availableGeometry, not geometry, because the taskbar is not.
		handle = self.windowHandle()
		screen = handle.screen() if handle else self._app.primaryScreen()
		frame = self.frameGeometry()
		frame.moveCenter(screen.availableGeometry().center())
		self.move(frame.topLeft())
	def is_title_bar_visible(self):
		return not self.windowFlags() & Qt.FramelessWindowHint
	@run_in_main_thread
	def set_title_bar_visible(self, visible):
		if visible == self.is_title_bar_visible():
			return
		# setWindowFlags recreates the native window, which hides it and
		# forgets both the frame position and - on Windows - the layered bit
		# behind setWindowOpacity. Restore all three. None of it applies
		# before show(), which is how startup gets here without a flash.
		# See fman.impl.window_chrome.
		was_visible = self.isVisible()
		# Keep the space on screen, not the client area: dropping the title bar
		# lets the client area grow over the frame it loses (geometry ->
		# frameGeometry), and putting the bar back restores the framed geometry
		# from before, so the window ends up exactly the size it started at.
		geometry = self.geometry()
		if was_visible:
			if visible:
				geometry = self._framed_geometry or geometry
			else:
				self._framed_geometry = geometry
				geometry = self.frameGeometry()
		opacity = self.windowOpacity()
		self.setWindowFlag(Qt.FramelessWindowHint, not visible)
		if was_visible:
			self.setGeometry(geometry)
			self.setWindowOpacity(opacity)
			self.show()
	@run_in_main_thread
	def set_status_bar_visible(self, visible):
		# An ordinary child widget, unlike the other two bars: no window flags,
		# no native menu. QMainWindow's layout gives the row to the central
		# widget when it is hidden, so the panes grow into it and the window
		# keeps its size. See fman.impl.window_chrome.
		self._status_bar.setVisible(visible)
	@run_in_main_thread
	def set_menu_bar_visible(self, visible):
		# Hides the Help menu, not the bar around it. Hiding the QMenuBar
		# achieves nothing either way: off Mac it holds no actions (and
		# menuBar() would create that empty bar here just to hide it), and on
		# Mac it is the native system bar, which ignores setVisible. What Qt
		# does propagate to the native bar is the menu's own QAction.
		# See fman.impl.window_chrome.
		if self._help_menu is None:
			return
		self._help_menu.menuAction().setVisible(visible)
	def showEvent(self, *args):
		super().showEvent(*args)
		# singleShot after 50 ms (not 0) ensures that the window is already
		# fully visible. Any alerts we show in response to .shown are then
		# placed correctly over the center of the window.
		QTimer(self).singleShot(50, self.shown.emit)
	def closeEvent(self, _):
		self.closed.emit()
	@run_in_main_thread
	def show_overlay(self, overlay):
		overlay.resize(overlay.sizeHint())
		self._position_overlay(overlay)
		overlay.show()
		# Above the Scrim, which is raised over the window while a dialog is
		# open - the tour's instructions are needed most at exactly that moment.
		overlay.raise_()
	def _position_overlay(self, overlay):
		bottom_inset = \
			self._status_bar.height() if self._status_bar.isVisible() else 0
		overlay.move(_overlay_pos(
			self.size(), overlay.size(), bottom_inset, self._dialog_rect()
		))
	def _dialog_rect(self):
		"""
		Where the open dialog (command palette, GoTo, ...) sits in this
		window's coordinates, or None if no dialog is open.
		"""
		if self._dialog is None:
			return None
		geometry = self._dialog.frameGeometry()
		return QRect(self.mapFromGlobal(geometry.topLeft()), geometry.size())
	def saveState(self, version=0):
		self_state = super().saveState(version)
		splitter_state = self._splitter.saveState()
		return self_state + splitter_state + bytes([len(self_state)])
	def restoreState(self, state, version=0):
		self_state_len = state[-1]
		if not super().restoreState(state[0:self_state_len], version):
			return False
		self._splitter.restoreState(state[self_state_len:-1])
		return True
	def focusNextPrevChild(self, next):
		# Returning False here lets us receive Tab in keyPressEvent(...).
		# This in turn lets us define our own key binding for the Tab key.
		return False

class MessageBox(QMessageBox):

	shown = pyqtSignal()

	# Width floor for the message text, in characters. Wide enough that a short
	# sentence is not broken up, narrow enough that a one-line message does not
	# produce a comically wide box.
	_MIN_TEXT_CHARS = 44
	# Never claim more than this share of the screen, so the floor cannot push
	# the box off-screen under a large theme font.
	_MAX_SCREEN_SHARE = .5

	def __init__(self, parent, allow_escape=True):
		super().__init__(parent)
		self._allow_escape = allow_escape
		self._width_floor_applied = False
		# Qt right-aligns the buttons on Windows/Linux, which looks lopsided
		# in our narrow, icon-less message boxes:
		self.findChild(QDialogButtonBox).setCenterButtons(True)
	def _apply_layout_fixes(self):
		"""
		Give the message text a minimum width, and left-align it when it spans
		several lines.

		Without a floor, QMessageBox sizes itself purely from its label. Once the
		text is wide relative to the screen - which happens readily under a theme
		with a large font - Qt turns on word wrap and clamps the label, so even
		text that already contains explicit newlines is re-wrapped into a tall,
		narrow column that can run off the bottom of the screen.

		The floor is a spacer in the last layout row rather than a min-width in
		styles.qss: a stylesheet min-width pins the box to exactly that width for
		every message, so longer text is cut off (see the comment on
		`QMessageBox QLabel` there). A spacer only raises the minimum, leaving the
		box free to grow with its content.
		"""
		label = self.findChild(QLabel, 'qt_msgbox_label')
		if label is None:
			return
		# Centered text lines up with the centered buttons and suits a one-line
		# message, but reads poorly once it is a paragraph. Set here rather than
		# in styles.qss: a stylesheet `qproperty-alignment` is re-applied on every
		# polish, which silently undid this.
		if '\n' in self.text():
			label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
		else:
			label.setAlignment(Qt.AlignCenter)
		if self._width_floor_applied:
			return
		self._width_floor_applied = True
		char_width = label.fontMetrics().horizontalAdvance('0')
		screen = self.screen() or QApplication.primaryScreen()
		width = min(
			char_width * self._MIN_TEXT_CHARS,
			int(screen.availableGeometry().width() * self._MAX_SCREEN_SHARE)
		)
		layout = self.layout()
		layout.addItem(
			QSpacerItem(width, 0, QSizePolicy.Minimum, QSizePolicy.Fixed),
			layout.rowCount(), 0, 1, layout.columnCount()
		)
	def _fit_buttons(self):
		"""Qt's updateSize caps the box width, which can squeeze its buttons."""
		button_box = self.findChild(QDialogButtonBox)
		if button_box is None:
			return
		margins = self.layout().contentsMargins()
		needed = button_box.minimumSizeHint().width() + margins.left() + \
			margins.right()
		if self.width() < needed:
			screen = self.screen() or QApplication.primaryScreen()
			self.setFixedWidth(min(needed, screen.availableGeometry().width()))
	def setStandardButtons(self, buttons):
		super().setStandardButtons(buttons)
		if is_mac():
			# The shortcut keys don't work out of the box on Mac, even though
			# they are displayed by our theme. (The standard macOS theme does
			# not display them.) The code below ensures that they work.
			# We do have to perform these steps _here_ because self.button(...)
			# returns None when called from the constructor.
			for button, shortcut in (
				(self.Yes, Qt.Key_Y), (self.No, Qt.Key_N),
				(self.YesToAll, Qt.Key_A), (self.NoToAll, Qt.Key_O)
			):
				if buttons & button:
					self.button(button).setShortcut(
						QKeySequence(Qt.CTRL + shortcut)
					)
	def keyPressEvent(self, event):
		if self._allow_escape or event.key() != Key_Escape:
			super().keyPressEvent(event)
	def showEvent(self, event):
		# Before super(), so the box is laid out at its final size rather than
		# resizing once it is already on screen.
		self._apply_layout_fixes()
		super().showEvent(event)
		self._fit_buttons()
		self.shown.emit()
	def event(self, e):
		result = super().event(e)
		if e.type() == QEvent.LayoutRequest:
			self._fit_buttons()
		return result

class Prompt(QInputDialog):
	"""
	Most of the code in this otherwise simple class solves the following
	problem: Say we want the user to enter a file path, and we want to
	pre-select the default file's base name without the extension. The file path
	is likely too long to be contained in the text field. We want to see:

		/path/to/my/file.txt
			 |      ----   |

	where --- is the selection and |   | are the visible borders of the text
	field. Instead, by default we see:

		/path/to/my/file.txt
		  |         ----|

	In other words, "file" is highlighted but the ".txt" suffix is cut off.

	QInputDialog and thus this class use QLineEdit for text input. That class
	internally uses a `hscroll` parameter to indicate the horizontal scroll
	position which distinguishes the two figures above. The problem is,
	`hscroll` is not settable from the outside. In fact, it is only set by
	QLineEdit::paintEvent(...). We thus perform the initial paintEvent(...)
	twice: First with the cursor at the end and then with the cursor / selection
	at the correct position. This sets `hscroll` to the required value.
	"""

	shown = pyqtSignal()

	def __init__(
		self, parent, title, text, default='', selection_start=0,
		selection_end=None
	):
		super().__init__(parent)
		self.setWindowTitle(title)
		self.setLabelText(text)
		self._selection_start = selection_start
		self._selection_end = selection_end
		if default:
			self.setTextValue(default)
		self.setTextEchoMode(QLineEdit.Normal)
		self._request_immediate_repaint = False
		self._is_second_paint = False
	def setVisible(self, visible):
		"""
		Unfortunately, our double call to paintEvent(...) leads to flickering
		effects on slower systems. The super() implementation of this function
		selects the text edit's entire text. This makes the flickering effect
		especially noticeable. To alleviate this, we only place the cursor at
		the end of the text field (via .end(...)). This still has the desired
		effect of getting Qt to not cut off the rightmost characters of the text
		field, yet has less visual effect.
		"""
		if visible:
			self.labelText() # Call private ensureLayout() of the superclass
			self._get_line_edit().end(False)
			self._request_immediate_repaint = True
		QDialog.setVisible(self, visible)
	def paintEvent(self, e):
		if self._request_immediate_repaint:
			self._request_immediate_repaint = False
			# Request the second paint:
			self.update()
			self._is_second_paint = True
		elif self._is_second_paint:
			self._is_second_paint = False
			self._set_cursor_and_selection()
	def showEvent(self, event):
		super().showEvent(event)
		self.shown.emit()
	def _set_cursor_and_selection(self):
		line_edit = self._get_line_edit()
		set_selection(line_edit, self._selection_start, self._selection_end)
	def _get_line_edit(self):
		for child in self.children():
			if isinstance(child, QLineEdit):
				return child
		raise AssertionError('Should not reach here')

class Splitter(QSplitter):
	def createHandle(self):
		result = QSplitterHandle(self.orientation(), self)
		result.installEventFilter(self)
		return result
	def eventFilter(self, splitter_handle, event):
		if event.type() == QEvent.MouseButtonDblClick:
			self._distribute_handles_evenly(splitter_handle.width())
			return True
		return False
	def _distribute_handles_evenly(self, handle_width):
		width_increment = self.width() // self.count()
		for i in range(1, self.count()):
			self.moveSplitter(i * width_increment - handle_width // 2, i)

ARROW_KEY_OFFSETS = {
	Qt.Key_Left: -1, Qt.Key_Up: -1, Qt.Key_Right: 1, Qt.Key_Down: 1
}

class Overlay(QFrame):

	"""
	The tutorial's speech bubble. `takes_focus` decides who owns the keyboard
	while it is up: with it off (the default) the directory pane keeps focus,
	so the user can carry out the step's instructions - navigate, press Tab,
	press F5 - and the overlay's buttons are mouse-only. With it on, the
	last button (the affirmative one, by convention) starts focused, the arrow
	keys move between the buttons and Enter activates the focused one - for
	steps whose only remaining action is "go on".
	"""

	def __init__(self, parent, html, buttons=None, takes_focus=False):
		super().__init__(parent)
		self._takes_focus = takes_focus
		self._default_button = None
		self._focusable_buttons = []
		self._focus_before_show = None

		self.setFrameShape(QFrame.Box)
		self.setFrameShadow(QFrame.Raised)
		self.setFocusPolicy(Qt.NoFocus)

		layout = QVBoxLayout()
		layout.setContentsMargins(20, 20, 20, 20)

		self.label = QLabel(self)
		self.label.setWordWrap(True)
		self.label.setText(html)

		# The following two lines prevent the label from being "cut off" at the
		# bottom under some circumstances:
		layout.setSizeConstraint(layout.SetMinAndMaxSize)
		self.label.setSizePolicy(
			QSizePolicy.MinimumExpanding, QSizePolicy.Minimum
		)

		layout.addWidget(self.label)

		if buttons:
			button_container = QWidget(self)
			button_layout = QHBoxLayout()
			for button_label, action in buttons:
				button = QPushButton(button_label, button_container)
				button.clicked.connect(lambda *_, action=action: action())
				if takes_focus:
					button.setFocusPolicy(Qt.StrongFocus)
					# Enter activates whichever button has focus. Qt draws that
					# one as the default button, so the user can see where
					# Enter would go.
					button.setAutoDefault(True)
					# For the arrow keys - see #eventFilter(...):
					button.installEventFilter(self)
					self._focusable_buttons.append(button)
				else:
					# Prevent button from stealing focus from the directory
					# pane:
					button.setFocusPolicy(Qt.NoFocus)
				button_layout.addWidget(button)
				self._default_button = button
			if takes_focus:
				# The affirmative button is the one Enter hits to begin with.
				self._default_button.setDefault(True)
			button_container.setLayout(button_layout)
			layout.addWidget(button_container)

		self.setLayout(layout)
	def eventFilter(self, watched, event):
		# Qt only moves focus with Tab/Backtab, and MainWindow claims Tab for
		# switching panes (see its #focusNextPrevChild(...)). So we move focus
		# between our buttons ourselves, on the arrow keys the rest of fman
		# uses for navigation. The buttons' Alt+letter mnemonics ("&Yes") work
		# regardless of focus and stay as a shortcut.
		if event.type() == QEvent.KeyPress:
			offset = ARROW_KEY_OFFSETS.get(event.key())
			if offset is not None and self._focus_button(watched, offset):
				return True
		return super().eventFilter(watched, event)
	def _focus_button(self, from_button, offset):
		buttons = self._focusable_buttons
		if len(buttons) < 2 or from_button not in buttons:
			return False
		index = (buttons.index(from_button) + offset) % len(buttons)
		buttons[index].setFocus(Qt.OtherFocusReason)
		return True
	def showEvent(self, event):
		super().showEvent(event)
		if self._takes_focus and self._default_button is not None:
			self._focus_before_show = QApplication.focusWidget()
			self._default_button.setFocus(Qt.OtherFocusReason)
	def close(self):
		self._restore_focus()
		self.setParent(None)
	def _restore_focus(self):
		if self._focus_before_show is None:
			return
		try:
			# Hand the keyboard back to the directory pane, so the next tour
			# step's instructions ("press Tab", "type its name") reach it:
			self._focus_before_show.setFocus(Qt.OtherFocusReason)
		except RuntimeError:
			# The widget that had focus is gone - it was a dialog that has
			# since been closed. Qt then picks the next focus target itself.
			pass
		self._focus_before_show = None

class Scrim(QFrame):

	"""
	Dims the main window while a modal dialog is open, so the dialog reads
	against the file list instead of competing with it. Its color - and thus
	how strong the dim is, in the alpha byte - is the theme's `scrim_bg`.
	"""

	def __init__(self, parent):
		super().__init__(parent)
		# Like Overlay: never take focus away from the directory pane.
		self.setFocusPolicy(Qt.NoFocus)
		self.setGeometry(parent.rect())
		self.raise_()
	def close(self):
		self.setParent(None)

class ProgressDialog(QProgressDialog):

	"""
	Instead of using @run_in_main_thread on #set_text(...) and
	#set_progress(...), this class uses #_update_timer to only update the GUI
	every 100ms. This avoids the unnecessary overhead of syncing with the main
	thread for every status update, and thus improves performance.
	"""

	_MAX_C_INT = 2147483647
	_MINIMUM_DURATION_MS = 1000
	_UPDATE_INTERVAL_MS = 100

	@run_in_main_thread
	def __init__(self, parent, title, size, progress_bar_palette):
		# Would like the dialog to be non-resizable on all platforms, but only
		# Windows supports it as a flag. On other platforms, we use
		# setFixedSize(...). See #resizeEvent(...) below.
		args = (Qt.MSWindowsFixedSizeDialogHint,) if is_windows() else ()
		super().__init__(parent, *args)
		self._title = title
		self._size = self.maximum()
		self._text = ''
		self._progress = 0
		self._was_canceled = False
		self._workers_label = None
		self._bar = self.findChild(QProgressBar)
		self._bar.setPalette(progress_bar_palette)
		# Looked up now: the workers label adds buttons of its own later.
		self._cancel_button = self.findChild(QPushButton)
		self.setMinimumDuration(self._MINIMUM_DURATION_MS)
		self.setAutoReset(False)
		self.setWindowTitle(title)
		self.set_task_size(size)
		self.canceled.disconnect(super().cancel)
		self.canceled.connect(self.request_cancel)
		self._update_timer = QTimer(self)
		self._update_timer.timeout.connect(self._update)
		# Ensure the progress dialog appears in 1 sec starting *now*:
		self.setValue(0)
	def set_text(self, text):
		self._text = text
	@run_in_main_thread
	def set_task_size(self, size):
		self._size = size
		self.setMaximum(min(size, self._MAX_C_INT))
	def set_progress(self, progress):
		self._progress = progress
	def get_progress(self):
		return self._progress
	def reject(self):
		# Called when the user presses the "Close window" button.
		self.request_cancel()
	@run_in_main_thread
	def cancel(self):
		super().cancel()
	@run_in_main_thread
	def request_cancel(self):
		self.set_text('Canceling...')
		self._cancel_button.setEnabled(False)
		self._was_canceled = True
	@run_in_main_thread
	def show_alert(self, *args, **kwargs):
		# Prevent the progress dialog from popping up while the alert is shown:
		self.setMinimumDuration(self._MAX_C_INT)
		try:
			return self.parent().show_alert(*args, **kwargs)
		finally:
			self.setMinimumDuration(self._MINIMUM_DURATION_MS)
	def was_canceled(self):
		return self._was_canceled
	@run_in_main_thread
	def show_workers(self, workers):
		self._workers_label = WorkersLabel(workers, self)
		self.setLabel(self._workers_label)
		self.installEventFilter(self)
		self._cancel_button.installEventFilter(self)
	def eventFilter(self, obj, e):
		# Filters the focused Cancel button too: it uses Up / Down itself.
		if e.type() != QEvent.KeyPress:
			return False
		if e.key() == Qt.Key_P and e.modifiers() & Qt.ControlModifier and \
				e.modifiers() & Qt.ShiftModifier:
			self._workers_label.open_palette(
				self.parent().show_quicksearch, self.request_cancel
			)
			return True
		return self._workers_label.handle_key(e.key())
	def showEvent(self, e):
		self._update()
		self._update_timer.start(self._UPDATE_INTERVAL_MS)
		super().showEvent(e)
	def closeEvent(self, e):
		self._update_timer.stop()
		super().closeEvent(e)
	def resizeEvent(self, e):
		super().resizeEvent(e)
		# Prevent the dialog from being resizable:
		if not is_windows():
			self.setFixedSize(self.size())
		if self._workers_label is not None:
			self._workers_label.place_file_count(
				self._bar, self._cancel_button
			)
	def _update(self):
		if self.wasCanceled():
			return
		if self._workers_label is None:
			self.setLabelText(self._text)
		# QLabel#setText(...) is not virtual, so setLabelText(...) would not
		# reach the workers label's own text.
		elif self._workers_label.refresh(self._text):
			self.adjustSize()
		self._set_value(self._progress)
	def _set_value(self, progress):
		if self._size > self._MAX_C_INT:
			# QProgressDialog#setValue(...) can only handle ints. If `progress`
			# is too large, we need to scale it down. If we didn't do this and
			# pass a larger number, it would overflow to a negative value.
			progress = self._MAX_C_INT * progress // self._size
		self.setValue(progress)
