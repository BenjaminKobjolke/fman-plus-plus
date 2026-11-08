from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication


def highlight(text):
	# The app palette carries the theme's bright_fg and follows theme switches.
	color = QApplication.palette().color(QPalette.WindowText).name()
	return "<span style='color: %s;'>%s</span>" % (color, text)

def underline(text):
	return "<span style='text-decoration: underline;'>%s</span>" % text
