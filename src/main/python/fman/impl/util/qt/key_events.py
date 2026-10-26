"""Parse and post Qt key events for demos and UI automation."""

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeyEvent, QKeySequence
from PyQt5.QtWidgets import QApplication

_MODIFIER_MASK = int(
	Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier
	| Qt.KeypadModifier | Qt.GroupSwitchModifier
)


def parse_chord(chord):
	sequence = QKeySequence(chord)
	if sequence.count() != 1:
		raise ValueError('Not a single key chord: %r' % chord)
	combo = sequence[0]
	return combo & ~_MODIFIER_MASK, Qt.KeyboardModifiers(combo & _MODIFIER_MASK)


def post_chord(target, chord):
	key, modifiers = parse_chord(chord)
	QApplication.postEvent(target, QKeyEvent(QEvent.KeyPress, key, modifiers))
	QApplication.postEvent(target, QKeyEvent(QEvent.KeyRelease, key, modifiers))


def post_text(target, text):
	for char in text:
		sequence = QKeySequence(char.upper())
		key = sequence[0] & ~_MODIFIER_MASK if sequence.count() else Qt.Key_unknown
		QApplication.postEvent(
			target, QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier, char))
		QApplication.postEvent(
			target, QKeyEvent(QEvent.KeyRelease, key, Qt.NoModifier, char))
