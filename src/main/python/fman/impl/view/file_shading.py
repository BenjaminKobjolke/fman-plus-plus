"""Paint graded file shading in the shared file-list delegate."""
from fman.impl.model.shading import SHADE_TINT, SHADE_TRANSPARENCY, ShadeRole
from PyQt5.QtWidgets import QStyle, QStyleOptionViewItem
from PyQt5.QtGui import QIcon


MIN_OPACITY = 0.4


def paint_shaded(paint, painter, option, index):
	shade = index.data(ShadeRole)
	if shade is None or option.state & (
		QStyle.State_Selected | QStyle.State_HasFocus
	):
		paint(painter, option, index)
		return
	if shade.style == SHADE_TRANSPARENCY:
		painter.save()
		try:
			painter.setOpacity(max(
				MIN_OPACITY, 1 - (1 - MIN_OPACITY) * shade.amount
			))
			paint(painter, option, index)
		finally:
			painter.restore()
		return
	paint(painter, option, index)
	if shade.style == SHADE_TINT:
		painter.save()
		try:
			painter.setOpacity(1 - shade.amount)
			overlay = QStyleOptionViewItem(option)
			overlay.state |= QStyle.State_On
			overlay.icon = QIcon()
			overlay.features &= ~QStyleOptionViewItem.HasDecoration
			paint(painter, overlay, index)
		finally:
			painter.restore()
