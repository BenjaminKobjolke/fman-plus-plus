"""Paint per-file text colors in the shared file-list delegate."""
from fman.impl.model.coloring import ColorRole
from fman.impl import themes
from PyQt5.QtGui import QColor, QFontMetrics
from PyQt5.QtWidgets import QApplication, QStyle, QStyleOptionViewItem


def paint_colored(delegate, paint, painter, option, index):
	color = index.data(ColorRole)
	if color is None or option.state & (
		QStyle.State_Selected | QStyle.State_HasFocus | QStyle.State_On
	):
		paint(painter, option, index)
		return

	opt = QStyleOptionViewItem(option)
	delegate.initStyleOption(opt, index)
	text = opt.text
	opt.text = ''
	style = opt.widget.style() if opt.widget else QApplication.style()
	style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

	text_rect = style.subElementRect(
		QStyle.SE_ItemViewItemText, opt, opt.widget
	)
	margin = style.pixelMetric(QStyle.PM_FocusFrameHMargin, opt, opt.widget) + 1
	text_rect.adjust(margin, 0, -margin, 0)
	text = QFontMetrics(opt.font).elidedText(
		text, opt.textElideMode, text_rect.width()
	)
	color = QColor(color)
	if not opt.state & QStyle.State_Enabled:
		color.setAlphaF(color.alphaF() * themes._HIDDEN_OPACITY)
	painter.setPen(color)
	painter.drawText(text_rect, opt.displayAlignment, text)
