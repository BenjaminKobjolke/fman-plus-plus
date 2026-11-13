from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import traceback


# Draw a row's text in a file-specific color.
ColorRole = Qt.UserRole + 3

_failed_colorer_ids = set()


def safe_color(colorer, url):
	if colorer is None:
		return None
	try:
		color = colorer(url)
	except Exception:
		# PyQt aborts the app on exceptions raised from a data() override.
		colorer_id = id(colorer)
		if colorer_id not in _failed_colorer_ids:
			_failed_colorer_ids.add(colorer_id)
			traceback.print_exc()
		return None
	if isinstance(color, QColor) and color.isValid():
		return color
	return None
