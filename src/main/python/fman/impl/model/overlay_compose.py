"""Paint a Windows shell overlay over an icon-set icon."""

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPainter, QPixmap

_ICON_SIZES = (16, 32, 48)


def compose_overlay(icon: QIcon, overlay: QPixmap) -> QIcon:
	"""Return `icon` with `overlay` drawn as a lower-left status badge."""
	if overlay.isNull():
		return icon

	result = QIcon()
	for size in _ICON_SIZES:
		base = icon.pixmap(QSize(size, size))
		if base.isNull():
			continue
		badge_size = max(1, size // 2)
		badge = overlay.scaled(
			QSize(badge_size, badge_size), Qt.KeepAspectRatio,
			Qt.SmoothTransformation
		)
		painter = QPainter(base)
		painter.drawPixmap(0, size - badge.height(), badge)
		painter.end()
		result.addPixmap(base)
	return result if not result.isNull() else icon
