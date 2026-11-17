from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PyQt5.QtCore import QEvent, QModelIndex, Qt, QAbstractTableModel
from PyQt5.QtWidgets import QApplication, QTableView

from fman.impl.scripting.external_drop import (
	DropRequest, DropTargetMissing, drop_files,
)


class ExternalDropTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.directory = TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		self.source = Path(self.directory.name, 'source.txt')
		self.source.write_text('drop fixture', encoding='utf-8')
		self.folder = Path(self.directory.name, 'folder')
		self.folder.mkdir()
		patcher = patch(
			'fman.impl.scripting.external_drop.fs.is_dir',
			return_value=True)
		patcher.start()
		self.addCleanup(patcher.stop)
		self.model = _Model(self.folder.as_uri())
		self.view = _View(self.model)
		self.view.setFixedSize(200, 120)
		self.view.show()
		self.addCleanup(self.view.close)
		self.app.processEvents()

	def test_drop_builds_file_urls_and_targets_the_folder_row(self):
		result = drop_files(self.view, DropRequest(
			0, [str(self.source)], onto=self.folder.as_uri(), action='copy'))

		self.assertTrue(result.accepted)
		self.assertEqual('copy', result.drop_action)
		self.assertEqual(self.folder.as_uri(), result.dest)
		self.assertEqual([0], [index.row() for index in self.view.model().targets])
		self.assertEqual([self.source.as_posix()] * 3,
			self.view.received_urls)

	def test_copy_and_move_use_the_platform_modifiers(self):
		cases = (
			('is_windows', {'copy': Qt.ControlModifier,
				'move': Qt.ShiftModifier, 'default': Qt.NoModifier}),
			('is_mac', {'copy': Qt.AltModifier,
				'move': Qt.NoModifier, 'default': Qt.NoModifier}),
			('is_linux', {'copy': Qt.ControlModifier,
				'move': Qt.NoModifier, 'default': Qt.NoModifier}),
		)
		for platform, actions in cases:
			for action, modifier in actions.items():
				with self.subTest(platform=platform, action=action):
					self.view.modifiers.clear()
					with patch(
						'fman.impl.scripting.external_drop.is_windows',
						return_value=platform == 'is_windows',
					), patch(
						'fman.impl.scripting.external_drop.is_mac',
						return_value=platform == 'is_mac',
					), patch(
						'fman.impl.scripting.external_drop.is_linux',
						return_value=platform == 'is_linux',
					):
						drop_files(self.view, DropRequest(
							0, [str(self.source)], action=action))
					self.assertTrue(self.view.modifiers)
					self.assertTrue(all(
						value == modifier for value in self.view.modifiers))

	def test_folder_target_rejects_a_file_row(self):
		self.model.directory = False
		with patch('fman.impl.scripting.external_drop.fs.is_dir',
				return_value=False):
			with self.assertRaises(DropTargetMissing):
				drop_files(self.view, DropRequest(
					0, [str(self.source)], onto=self.folder.as_uri()))

	def test_default_target_is_below_the_last_row(self):
		drop_files(self.view, DropRequest(0, [str(self.source)]))
		self.assertGreater(self.view.points[-1].y(),
			self.view.visualRect(self.model.index(0, 0)).bottom())

	def test_default_target_rejects_point_outside_viewport(self):
		self.view.viewport().setFixedSize(200, 15)
		self.app.processEvents()
		with self.assertRaises(DropTargetMissing):
			drop_files(self.view, DropRequest(0, [str(self.source)]))


class _Model(QAbstractTableModel):
	def __init__(self, folder):
		super().__init__()
		self.folder = folder
		self.directory = True
		self.targets = []

	def rowCount(self, parent=None):
		return 1

	def columnCount(self, parent=None):
		return 1

	def data(self, index, role=None):
		return ''

	def url(self, index):
		return self.folder

	def drop_dest_url(self, index):
		self.targets.append(index)
		return self.folder

	def find(self, url):
		return self.index(0, 0) if url == self.folder else QModelIndex()


class _View(QTableView):
	def __init__(self, model):
		super().__init__()
		self.setModel(model)
		self.setAcceptDrops(True)
		self.viewport().setAcceptDrops(True)
		self.received_urls = []
		self.modifiers = []
		self.points = []

	def viewportEvent(self, event):
		if event.type() in (
			QEvent.DragEnter, QEvent.DragMove, QEvent.Drop,
		):
			self.modifiers.append(event.keyboardModifiers())
			self.points.append(event.pos())
			self.received_urls.extend(
				url.toLocalFile() for url in event.mimeData().urls())
			event.setDropAction(Qt.CopyAction)
			event.accept()
			return True
		return super().viewportEvent(event)
