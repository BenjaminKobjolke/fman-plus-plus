from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtWidgets import QWidget


class _HeaderSpacer(QObject):
	def __init__(self, view):
		super().__init__(view)
		self._view = view
		self._header = view.horizontalHeader()
		self._spacer = QWidget()
		self._spacer.setObjectName('scrollbar_header_spacer')
		self._update_size()
		view.addScrollBarWidget(self._spacer, Qt.AlignTop)
		self._header.installEventFilter(self)
	def eventFilter(self, watched, event):
		if watched is self._header and event.type() == QEvent.Resize:
			self._update_size()
		return False
	def _update_size(self):
		width = self._view.verticalScrollBar().sizeHint().width()
		self._spacer.setFixedSize(width, self._header.height())


def install_scrollbar_below_header(view):
	"""Reserve a header-height spacer above the vertical scroll bar."""
	_HeaderSpacer(view)
