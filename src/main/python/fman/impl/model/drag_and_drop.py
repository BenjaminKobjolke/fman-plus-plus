from fman.impl.util.qt import MoveAction, CopyAction, IgnoreAction, \
	FMAN_URLS_MIME, get_urls, set_urls
from fman.url import dirname
from PyQt5.QtCore import QAbstractTableModel, pyqtSignal, QMimeData

import sip

class DragAndDrop(QAbstractTableModel):

	files_dropped = pyqtSignal(list, str, bool)

	def url(self, index):
		raise NotImplementedError('Must be implemented by subclasses')
	def get_location(self):
		raise NotImplementedError('Must be implemented by subclasses')
	def supportedDropActions(self):
		return MoveAction | CopyAction | IgnoreAction
	def canDropMimeData(self, data, action, row, column, parent):
		if not action & self.supportedDropActions():
			return False
		if not data.hasUrls():
			return False
		urls = get_urls(data)
		if not urls:
			return False
		dest_dir = self._get_drop_dest(parent)
		def is_in_dest_dir(url):
			return dirname(url) == dest_dir
		return not all(map(is_in_dest_dir, urls))
	def mimeTypes(self):
		"""
		List the MIME types used by our drag and drop implementation.
		"""
		return ['text/uri-list', FMAN_URLS_MIME]
	def mimeData(self, indexes):
		result = QMimeData()
		set_urls(result, [self.url(index) for index in indexes])
		# The Qt documentation (http://doc.qt.io/qt-5/dnd.html) states that the
		# QMimeData should not be deleted, because the target of the drag and
		# drop operation takes ownership of it. We must therefore tell SIP not
		# to garbage-collect `result` once this method returns. Without this
		# instruction, we get a horrible crash because Qt tries to access an
		# object that has already been gc'ed:
		sip.transferto(result, None)
		return result
	def dropMimeData(self, data, action, row, column, parent):
		if action == IgnoreAction:
			return True
		if not data.hasUrls():
			return False
		urls = get_urls(data)
		dest = self._get_drop_dest(parent)
		if action in (MoveAction, CopyAction):
			self.files_dropped.emit(urls, dest, action == CopyAction)
			return True
		return False
	def _get_drop_dest(self, index):
		return self.url(index) if index.isValid() else self.get_location()
