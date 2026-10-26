"""Syntax coloring for the Core text viewer, bounded to keep large files responsive."""

from pygments import lex
from pygments.lexers import get_lexer_for_filename
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat


MAX_HIGHLIGHT_CHARS = 512 * 1024


def lexer_for_path(path):
	if path is None:
		return None
	try:
		return get_lexer_for_filename(str(path))
	except ClassNotFound:
		return None


def split_spans(tokens, text):
	spans = [[] for _ in range(text.count('\n') + 1)]
	line = 0
	column = 0
	for token, value in tokens:
		parts = value.split('\n')
		for index, part in enumerate(parts):
			if index < len(parts) - 1 and part.endswith('\r'):
				part = part[:-1]
			if part:
				spans[line].append((column, len(part), token))
			column += len(part)
			if index < len(parts) - 1:
				line += 1
				column = 0
	return spans


def get_spans(text, path):
	if len(text) > MAX_HIGHLIGHT_CHARS:
		return []
	lexer = lexer_for_path(path)
	if lexer is None:
		return []
	return split_spans(lex(text, lexer), text)


def style_name_for_background(background):
	color = QColor(background)
	return 'monokai' if color.isValid() and color.lightness() < 128 else 'default'


def _format_for_token(token, style):
	values = style.style_for_token(token)
	result = QTextCharFormat()
	if values['color']:
		result.setForeground(QColor('#' + values['color']))
	if values['bgcolor']:
		result.setBackground(QColor('#' + values['bgcolor']))
	if values['bold']:
		result.setFontWeight(75)
	if values['italic']:
		result.setFontItalic(True)
	if values['underline']:
		result.setFontUnderline(True)
	return result


class PygmentsHighlighter(QSyntaxHighlighter):
	def __init__(self, view, background):
		super().__init__(view.document())
		self._view = view
		self._path = view._path
		self._style = get_style_by_name(style_name_for_background(background))
		self._formats = {}
		self._spans = []
		self._enabled = True
		self._timer = QTimer(view)
		self._timer.setSingleShot(True)
		self._timer.setInterval(0)
		self._timer.timeout.connect(self._relex)
		view.document().contentsChange.connect(self._contents_changed)
		self._relex()

	def set_path(self, path):
		self._path = path
		self._relex()

	def set_editing(self, editing):
		self._timer.setInterval(300 if editing else 0)

	def set_enabled(self, enabled):
		self._enabled = enabled
		self.rehighlight()

	def _contents_changed(self, position, chars_removed, chars_added):
		if chars_removed == 0 and chars_added == 0:
			return
		self._timer.start()

	def _relex(self):
		self._spans = get_spans(self._view.toPlainText(), self._path)
		self.rehighlight()

	def highlightBlock(self, text):
		if not self._enabled or self.currentBlock().blockNumber() >= len(self._spans):
			return
		for start, length, token in self._spans[self.currentBlock().blockNumber()]:
			if token not in self._formats:
				self._formats[token] = _format_for_token(token, self._style)
			self.setFormat(start, length, self._formats[token])


class ViewerSyntax:
	"""Per-view syntax-color toggle and its palette command."""
	def __init__(self, view, background):
		self._view = view
		self._enabled = True
		self._highlighter = PygmentsHighlighter(view, background)

	def actions(self):
		title = 'Disable syntax colors' if self._enabled else 'Enable syntax colors'
		return [(title, self.toggle_syntax_colors, '', 'text_toggle_syntax_colors')]

	def commands(self):
		return {'text_toggle_syntax_colors': self.toggle_syntax_colors}

	def set_editing(self, editing):
		self._highlighter.set_editing(editing)

	def toggle_syntax_colors(self):
		self._enabled = not self._enabled
		self._highlighter.set_enabled(self._enabled)
		if not self._enabled:
			message = 'Syntax colors off'
		elif len(self._view.toPlainText()) > MAX_HIGHLIGHT_CHARS:
			message = 'Syntax colors skipped for files over 512 KB'
		elif lexer_for_path(self._view._path) is None:
			message = 'No syntax colors available for this file'
		else:
			message = 'Syntax colors on'
		from core.viewer_status import viewer_status
		viewer_status(self._view._nav.pane, message)
