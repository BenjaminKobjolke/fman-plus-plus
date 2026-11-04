from fman.impl.background import chrome_is_transparent, for_pane, \
	focus_changes_pane, pane_is_transparent
from fman.impl.view.backgrounds import PAINTER, set_transparent
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPalette


class PaneSurface:
	"""Shared theme backgrounds and empty-pane text for pane views."""

	def set_backgrounds(self, backgrounds, pane_index):
		"""Set the theme backgrounds and pane position used when painting."""
		self._backgrounds = backgrounds
		self._pane_index = pane_index
		set_transparent(self, pane_is_transparent(backgrounds, pane_index))
		header = self._header()
		if header is not None:
			set_transparent(header, chrome_is_transparent(backgrounds))
		self.viewport().update()

	def set_loading(self, text):
		"""Show `text` while the pane has no rows yet."""
		self._loading_text = text
		self.viewport().update()

	def _paint_backgrounds(self):
		backgrounds = for_pane(
			self._backgrounds, self._pane_index, self.hasFocus()
		)
		if not backgrounds:
			# The viewport may still be transparent for a window background.
			return
		viewport = self.viewport()
		painter = QPainter(viewport)
		painter.fillRect(viewport.rect(), self.palette().color(QPalette.Base))
		PAINTER.paint(painter, viewport.rect(), backgrounds)

	def _paint_loading_text(self):
		painter = QPainter(self.viewport())
		painter.setPen(
			self.palette().color(QPalette.Disabled, QPalette.Text)
		)
		painter.drawText(
			self.viewport().rect().adjusted(16, 0, -16, 0),
			Qt.AlignCenter | Qt.TextWordWrap, self._loading_text
		)

	def _repaint_if_focus_matters(self):
		if focus_changes_pane(self._backgrounds, self._pane_index):
			self.viewport().update()
