"""
The worker rows a ProgressDialog shows while a copy runs on several workers,
and the buttons that add or remove workers.

Deliberately named `*_test.py` rather than `test_*.py`, so `python build.py
test` does not discover it: it needs a QApplication of its own, and stray Qt
state is what makes that suite hang (see CLAUDE.md). Run it via
tools\\run_progress_dialog_tests.bat.
"""

from dataclasses import dataclass
from fman.impl.widgets import MainWindow
from fman.impl.progress_dialog import ProgressDialog
from fman.impl.workers_label import elide_lines, WorkersLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtTest import QTest
from fman.impl.view import ProxyStyle
from PyQt5.QtWidgets import QApplication, QLabel, QStyle, QStyleFactory, \
	QWidget
from unittest import TestCase

class WorkersLabelTest(TestCase):
	def test_dialog_matches_hidden_main_window_title_bar(self):
		dialog = QWidget()
		MainWindow._match_title_bar(_FakeMainWindow(False), dialog)
		self.assertTrue(dialog.windowFlags() & Qt.FramelessWindowHint)
		# styles.qss outlines it, or it blends into the window behind it.
		self.assertTrue(dialog.property('frameless'))
	def test_dialog_keeps_title_bar_when_main_window_title_bar_is_visible(self):
		dialog = QWidget()
		MainWindow._match_title_bar(_FakeMainWindow(True), dialog)
		self.assertFalse(dialog.windowFlags() & Qt.FramelessWindowHint)
		self.assertFalse(dialog.property('frameless'))
	def test_frameless_dialog_keeps_its_content_off_the_outline(self):
		dialog, plain = QWidget(), QWidget()
		MainWindow._match_title_bar(_FakeMainWindow(False), dialog)
		style = ProxyStyle(QStyleFactory.create('Fusion'))
		for metric in (QStyle.PM_LayoutLeftMargin, QStyle.PM_LayoutBottomMargin):
			self.assertGreater(
				style.pixelMetric(metric, None, dialog),
				style.pixelMetric(metric, None, plain)
			)
	def test_frameless_dialog_keeps_the_app_style(self):
		# A style of its own would cut its buttons off the theme's stylesheet.
		dialog = QWidget()
		MainWindow._match_title_bar(_FakeMainWindow(False), dialog)
		self.assertIs(QApplication.style(), dialog.style())
	def test_always_frameless_dialog_gets_no_outline(self):
		# Like Quicksearch, which draws its own look.
		dialog = QWidget(None, Qt.FramelessWindowHint)
		MainWindow._match_title_bar(_FakeMainWindow(False), dialog)
		self.assertFalse(dialog.property('frameless'))
	def test_rows_show_title_and_percentage(self):
		label = self._label(
			_Worker(1, 'Downloading a.jpg', progress=45, size=100), _Worker(2)
		)
		self.assertEqual('#1\n#2', label._ids.text())
		self.assertEqual('45%\n', label._percents.text())
		self.assertEqual('Downloading a.jpg\n(idle)', label._titles.text())
	def test_size_hint_grows_with_the_rows_right_away(self):
		workers = _FakeWorkers()
		label = WorkersLabel(workers)
		before = label.sizeHint().height()
		workers.workers[:] = [_Worker(1), _Worker(2), _Worker(3)]
		# No event loop in between, like ProgressDialog#_update(...).
		label.refresh('')
		self.assertGreater(label.sizeHint().height(), before)
	def test_percent_column_fits_100_percent_in_the_current_font(self):
		label = WorkersLabel(_FakeWorkers(_Worker(1, 'a', size=100)))
		# Like fman's stylesheet, which applies after the label is created.
		label.setStyleSheet('QLabel { font-size: 40px; }')
		label.refresh('')
		percents = label._percents
		width = percents.fontMetrics().horizontalAdvance('100%')
		self.assertEqual(width, percents.minimumWidth())
		self.assertEqual(width, percents.maximumWidth())
	def test_long_titles_are_elided_in_the_middle_per_line(self):
		label = QLabel()
		metrics = label.fontMetrics()
		long = 'Deleting a_very_long_file_name_indeed.jpg  (finishing)'
		width = metrics.horizontalAdvance(long) // 2
		lines = elide_lines('short\n' + long, metrics, width).split('\n')
		self.assertEqual('short', lines[0])
		self.assertTrue(lines[1].startswith('Del'))
		self.assertTrue(lines[1].endswith('(finishing)'))
		self.assertLessEqual(metrics.horizontalAdvance(lines[1]), width)
	def test_title_column_may_get_narrower_than_its_text(self):
		label = self._label(_Worker(1, 'Copying ' + 'x' * 200))
		titles = label._titles
		self.assertLess(
			titles.minimumSizeHint().width(), titles.sizeHint().width()
		)
	def test_unknown_size_shows_no_percentage(self):
		label = self._label(_Worker(1, 'Copying a', size=0))
		self.assertEqual('', label._percents.text())
		self.assertEqual('Copying a', label._titles.text())
	def test_retiring_worker_is_marked(self):
		label = self._label(
			_Worker(1, 'Copying a'), _Worker(3, 'Copying b', retiring=True)
		)
		self.assertEqual(
			'Copying a\nCopying b  (finishing)', label._titles.text()
		)
		self.assertEqual('Threads: 1', label._count.text())
	def test_shows_file_count(self):
		workers = _FakeWorkers(_Worker(1))
		workers.file_counts = (3, 5)
		label = WorkersLabel(workers)
		self.assertEqual('3 / 5', label._files.text())
	def test_buttons_add_and_remove_workers(self):
		workers = _FakeWorkers(_Worker(1), _Worker(2))
		label = WorkersLabel(workers)
		label._add.click()
		label._remove.click()
		self.assertEqual(['add', 'remove'], workers.calls)
	def test_keys_add_and_remove_workers(self):
		dialog = self._dialog()
		workers = _FakeWorkers(_Worker(1), _Worker(2))
		dialog.show_workers(workers)
		# Sent to the Cancel button: it has the focus while the dialog shows.
		for key in (Qt.Key_Plus, Qt.Key_Up, Qt.Key_Minus, Qt.Key_Down):
			QTest.keyClick(dialog._cancel_button, key)
		QTest.keyClick(dialog._cancel_button, Qt.Key_Plus, Qt.KeypadModifier)
		self.assertEqual(
			['add', 'add', 'remove', 'remove', 'add'], workers.calls
		)
	def test_palette_lists_actions_with_their_shortcuts(self):
		workers = _FakeWorkers(_Worker(1), _Worker(2))
		palette = _FakePalette('Add thread')
		WorkersLabel(workers).open_palette(palette.show, lambda: None)
		self.assertEqual(
			[
				('Add thread', '+ / Up'), ('Remove thread', '- / Down'),
				('Cancel', 'Esc')
			],
			palette.rows('')
		)
		self.assertEqual([('Cancel', 'Esc')], palette.rows('CANC'))
		self.assertEqual(['add'], workers.calls)
	def test_palette_leaves_out_what_workers_do_not_allow(self):
		workers = _FakeWorkers(_Worker(1))
		workers.removable = False
		palette = _FakePalette(None)
		WorkersLabel(workers).open_palette(palette.show, lambda: None)
		self.assertNotIn('Remove thread', [t for t, _ in palette.rows('')])
		self.assertEqual([], workers.calls)
	def test_palette_key_opens_the_palette_in_the_dialog(self):
		parent = _PaletteParent('Cancel')
		dialog = self._dialog(parent)
		dialog.show_workers(_FakeWorkers(_Worker(1), _Worker(2)))
		QTest.keyClick(
			dialog._cancel_button, Qt.Key_P,
			Qt.ControlModifier | Qt.ShiftModifier
		)
		self.assertTrue(dialog.was_canceled())
	def test_buttons_follow_what_workers_allow(self):
		workers = _FakeWorkers(_Worker(1))
		workers.removable = False
		label = WorkersLabel(workers)
		self.assertFalse(label._remove.isEnabled())
		self.assertTrue(label._add.isEnabled())
	def test_refresh_reports_a_changed_row_count(self):
		workers = _FakeWorkers(_Worker(1), _Worker(2))
		label = WorkersLabel(workers)
		self.assertFalse(label.refresh(''))
		workers.workers.pop()
		self.assertTrue(label.refresh(''))
	def test_progress_dialog_shows_its_text_in_the_workers_label(self):
		dialog = self._dialog()
		dialog.show_workers(_FakeWorkers(_Worker(1)))
		dialog.set_text('Copying 3 files')
		dialog._update()
		self.assertEqual('Copying 3 files', dialog._workers_label._text.text())
	def test_cancel_disables_the_cancel_button_not_the_worker_buttons(self):
		dialog = self._dialog()
		dialog.show_workers(_FakeWorkers(_Worker(1), _Worker(2)))
		dialog.request_cancel()
		self.assertFalse(dialog._cancel_button.isEnabled())
		self.assertTrue(dialog._workers_label._add.isEnabled())
		self.assertTrue(dialog._workers_label._remove.isEnabled())
	def _dialog(self, parent=None):
		return ProgressDialog(parent, 'Copying', 100, QPalette())
	def _label(self, *workers):
		result = WorkersLabel(_FakeWorkers(*workers))
		result.refresh('')
		return result
	@classmethod
	def setUpClass(cls):
		# One QApplication per process; Qt refuses a second one.
		cls.app = QApplication.instance() or QApplication([])

@dataclass
class _Worker:
	id: int
	title: str = ''
	progress: int = 0
	size: int = 0
	retiring: bool = False

class _FakeWorkers:
	def __init__(self, *workers):
		self.workers = list(workers)
		self.calls = []
		self.removable = True
		self.file_counts = (0, 0)
	def snapshot(self):
		return list(self.workers)
	def add(self):
		self.calls.append('add')
	def remove(self):
		self.calls.append('remove')
	def can_add(self):
		return True
	def can_remove(self):
		return self.removable
	def counts(self):
		return self.file_counts

class _FakePalette:
	"""
	Stands in for MainWindow#show_quicksearch: picks the row titled `choice`.
	"""
	def __init__(self, choice):
		self._choice = choice
		self._get_items = None
	def show(self, get_items):
		self._get_items = get_items
		for item in get_items(''):
			if item.title == self._choice:
				return '', item.value
		return None
	def rows(self, query):
		return [(item.title, item.hint) for item in self._get_items(query)]

class _PaletteParent(QWidget):
	# ProgressDialog asks its parent - the main window - for the palette.
	def __init__(self, choice):
		super().__init__()
		self.show_quicksearch = _FakePalette(choice).show

class _FakeMainWindow:
	def __init__(self, title_bar_visible):
		self._title_bar_visible = title_bar_visible
	def is_title_bar_visible(self):
		return self._title_bar_visible
