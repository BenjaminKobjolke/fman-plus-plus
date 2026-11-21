from unittest import TestCase
from unittest.mock import patch

from PyQt5.QtCore import QEvent, QModelIndex, Qt, QAbstractTableModel
from PyQt5.QtWidgets import QApplication, QTableView

from fman.impl.scripting.automation import UnknownFile
from fman.impl.scripting.external_drop import DropTargetMissing
from fman.impl.scripting.pane_drag import (
	PaneDragRequest, drag_between, parse_pane_drag,
)


class PaneDragTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.source_model = _Model('file:///source.txt')
		self.target_model = _Model('file:///folder', directory=True)
		self.source_view = _View(self.source_model)
		self.target_view = _View(self.target_model)
		for view in (self.source_view, self.target_view):
			view.setFixedSize(200, 120)
			view.show()
			self.addCleanup(view.close)
		self.app.processEvents()

	def test_drag_sends_source_url_through_drop_events_to_target_folder(self):
		with patch('fman.impl.scripting.external_drop.fs.is_dir',
				return_value=True):
			result = drag_between(self.source_view, self.target_view,
				PaneDragRequest(0, ['file:///source.txt'], 1,
					'file:///folder', 'copy'))

		self.assertTrue(result.accepted)
		self.assertEqual('copy', result.drop_action)
		self.assertEqual('file:///folder', result.dest)
		self.assertEqual([0], [index.row() for index in self.target_model.targets])
		self.assertEqual(['file:///source.txt'] * 3,
			self.target_view.received_urls)
		self.assertEqual(['text/uri-list', 'application/x-fman-urls'],
			self.target_view.mime_formats)

	def test_onto_file_row_is_rejected(self):
		with patch('fman.impl.scripting.external_drop.fs.is_dir',
				return_value=False), self.assertRaises(DropTargetMissing):
			drag_between(self.source_view, self.target_view,
				PaneDragRequest(0, ['file:///source.txt'], 1,
					'file:///folder', 'default'))

	def test_file_not_shown_in_source_pane_is_rejected(self):
		with self.assertRaises(UnknownFile):
			drag_between(self.source_view, self.target_view,
				PaneDragRequest(0, ['file:///missing.txt'], 1, None, 'default'))

	def test_parse_pane_drag_validates_files_panes_and_action(self):
		request = parse_pane_drag({
			'source_pane': 0, 'files': ['file:///source.txt'], 'pane': 1,
			'onto': None, 'action': 'move',
		})
		self.assertEqual(PaneDragRequest(
			0, ['file:///source.txt'], 1, None, 'move'), request)
		for payload in (
			{'files': []},
			{'source_pane': True, 'files': ['file:///source.txt']},
			{'pane': False, 'files': ['file:///source.txt']},
			{'files': ['file:///source.txt'], 'action': 'teleport'},
		):
			with self.subTest(payload=payload), self.assertRaises(ValueError):
				parse_pane_drag(payload)


class _Model(QAbstractTableModel):
	def __init__(self, url, directory=False):
		super().__init__()
		self._url = url
		self.directory = directory
		self.targets = []

	def rowCount(self, parent=None):
		return 1

	def columnCount(self, parent=None):
		return 1

	def data(self, index, role=None):
		return ''

	def url(self, index):
		return self._url

	def drop_dest_url(self, index):
		self.targets.append(index)
		return self._url

	def find(self, url):
		return self.index(0, 0) if url == self._url else QModelIndex()


class _View(QTableView):
	def __init__(self, model):
		super().__init__()
		self.setModel(model)
		self.setAcceptDrops(True)
		self.viewport().setAcceptDrops(True)
		self.received_urls = []
		self.mime_formats = []
		self.modifiers = []

	def viewportEvent(self, event):
		if event.type() in (QEvent.DragEnter, QEvent.DragMove, QEvent.Drop):
			self.modifiers.append(event.keyboardModifiers())
			self.received_urls.extend(
				url.toString() for url in event.mimeData().urls())
			self.mime_formats = event.mimeData().formats()
			event.setDropAction(Qt.CopyAction)
			event.accept()
			return True
		return super().viewportEvent(event)
