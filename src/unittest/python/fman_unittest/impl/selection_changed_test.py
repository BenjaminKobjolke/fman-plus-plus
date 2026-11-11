"""Selection changes are debounced before reaching pane listeners."""

from fman import DirectoryPane
from fman.impl.controller import Controller
from fman.impl.plugins.plugin import ListenerWrapper
from fman.impl.widgets import DirectoryPaneWidget
from PyQt5.QtCore import (
	QItemSelection, QItemSelectionModel, QObject, pyqtSignal
)
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtTest import QSignalSpy, QTest
from PyQt5.QtWidgets import QApplication, QWidget
from threading import Event
from unittest import TestCase
from unittest.mock import MagicMock


_APP = QApplication.instance() or QApplication([])


class DirectoryPaneSelectionChangedTest(TestCase):

	def setUp(self):
		self.widget = DirectoryPaneWidget.__new__(DirectoryPaneWidget)
		QWidget.__init__(self.widget)

	def tearDown(self):
		self.widget.deleteLater()

	def test_burst_of_selection_changes_emits_once_after_debounce(self):
		model = QStandardItemModel(3, 1)
		selection_model = QItemSelectionModel(model)
		self.widget._file_view = MagicMock()
		self.widget._file_view.selectionModel.return_value = selection_model
		self.widget._connect_selection_changes()
		spy = QSignalSpy(self.widget.selection_changed)

		selection_model.selectionChanged.emit(QItemSelection(), QItemSelection())
		selection_model.selectionChanged.emit(QItemSelection(), QItemSelection())
		selection_model.selectionChanged.emit(QItemSelection(), QItemSelection())
		self.assertTrue(self.widget._selection_timer.isActive())
		QTest.qWait(175)

		self.assertEqual(1, len(spy))
		self.assertIs(self.widget, spy[0][0])


class ControllerSelectionChangedTest(TestCase):

	def setUp(self):
		self.controller = Controller(
			MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
		)
		self.pane_widget = _PaneWidget()
		self.pane = DirectoryPane(MagicMock(), MagicMock(), MagicMock())
		self.controller.register_pane(self.pane_widget, self.pane)

	def test_selection_change_broadcasts_to_registered_pane_listener(self):
		listener = _RecordingListener()
		self.pane._add_listener(listener)

		self.pane_widget.selection_changed.emit(self.pane_widget)

		self.assertEqual(1, listener.calls)

	def test_late_selection_change_is_ignored_after_unregister(self):
		self.controller.unregister_pane(self.pane_widget, self.pane)

		self.pane_widget.selection_changed.emit(self.pane_widget)


class ListenerWrapperSelectionChangedTest(TestCase):

	def test_selection_change_is_forwarded_on_listener_worker_thread(self):
		called = Event()
		listener = MagicMock()
		listener.on_selection_changed.side_effect = called.set
		wrapper = ListenerWrapper(listener, MagicMock())

		wrapper.on_selection_changed()

		self.assertTrue(called.wait(5))
		listener.on_selection_changed.assert_called_once_with()


class _RecordingListener:
	def __init__(self):
		self.calls = 0
	def on_selection_changed(self):
		self.calls += 1


class _PaneWidget(QObject):
	location_changed = pyqtSignal(object)
	location_bar_clicked = pyqtSignal(object)
	location_bar_segment_clicked = pyqtSignal(object, str)
	selection_changed = pyqtSignal(object)
