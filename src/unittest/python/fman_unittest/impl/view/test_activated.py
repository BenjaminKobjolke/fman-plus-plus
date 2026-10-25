from fman.impl.view import FileListView
from PyQt5.QtCore import QEvent
from PyQt5.QtGui import QFocusEvent
from PyQt5.QtWidgets import QApplication
from unittest import TestCase

_APP = QApplication.instance() or QApplication([])


class FileListViewActivationTest(TestCase):
	def test_emits_activated_when_it_receives_focus(self):
		view = FileListView(None, lambda *args: None)
		calls = []
		view.activated.connect(lambda: calls.append(True))

		view.focusInEvent(QFocusEvent(QEvent.FocusIn))

		self.assertEqual([True], calls)
