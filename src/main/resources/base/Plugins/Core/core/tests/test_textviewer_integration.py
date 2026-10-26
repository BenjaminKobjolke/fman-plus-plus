import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from core.textviewer import show_text_viewer
from core.textviewer_save import save
from fman.url import as_url
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch


_APP = QApplication.instance() or QApplication([])


class _Pane:
	def __init__(self):
		self._widget = QWidget()
		self._mounted = None
		self.status_messages = []

	def get_mounted_widget(self):
		return self._mounted

	def unmount_widget(self):
		self._mounted = None

	def get_colors(self):
		return '#ffffff', '#000000'

	def mount_widget(self, view, focus=True):
		self._mounted = view

	def show_status_message(self, text, timeout_secs=None):
		self.status_messages.append(text)

	def run_command(self, name):
		pass


class TextViewerIntegrationTest(TestCase):
	def test_open_edit_and_save_json_keeps_pretty_text(self):
		with TemporaryDirectory() as folder:
			path = Path(folder) / 'sample.json'
			path.write_text('{"name":"Ada","count":2}', encoding='utf-8')
			pane = _Pane()
			show_text_viewer(pane, as_url(str(path)))
			view = pane._mounted

			self.assertEqual(
				'{\n  "name": "Ada",\n  "count": 2\n}',
				view.toPlainText(),
			)
			view._enter_edit_mode()
			self.assertFalse(view.document().isModified())
			self.assertIn('Save reformats the file', pane.status_messages[-1])
			with patch('core.textviewer_save.notify_file_changed'):
				save(view)
			self.assertEqual(
				'{\n  "name": "Ada",\n  "count": 2\n}',
				path.read_text(encoding='utf-8'),
			)

	def test_rename_updates_syntax_lexer_for_new_extension(self):
		with TemporaryDirectory() as folder:
			path = Path(folder) / 'sample.json'
			path.write_text('{"name":"Ada"}', encoding='utf-8')
			pane = _Pane()
			show_text_viewer(pane, as_url(str(path)))
			view = pane._mounted

			new_path = Path(folder) / 'sample.unknownext'
			view._on_renamed(as_url(str(new_path)))

			self.assertEqual(str(new_path), view._syntax._highlighter._path)
			self.assertEqual([], view._syntax._highlighter._spans)
