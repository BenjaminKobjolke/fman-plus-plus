"""Pretty printing for text files shown by the Core text viewer."""
import json
import os
import re
from xml.dom import Node, minidom
from xml.parsers.expat import ExpatError


_JSON_EXTENSIONS = {'.json'}
_XML_EXTENSIONS = {
	'.config', '.html', '.htm', '.plist', '.rss', '.svg', '.wsdl', '.xhtml',
	'.xml', '.xsd', '.xsl', '.xslt',
}


def _extension(path):
	return os.path.splitext(path)[1].lower() if path else ''


def _remove_whitespace_text_nodes(node):
	for child in list(node.childNodes):
		if child.nodeType == Node.TEXT_NODE and not child.data.strip():
			node.removeChild(child)
			child.unlink()
		else:
			_remove_whitespace_text_nodes(child)


def _pretty_xml(text):
	declaration = re.match(r'^\ufeff?\s*(<\?xml\s+.*?\?>)', text, re.IGNORECASE)
	try:
		document = minidom.parseString(text)
		_remove_whitespace_text_nodes(document)
		formatted = document.toprettyxml(indent='  ')
	except (ExpatError, ValueError, TypeError):
		return None
	if declaration:
		generated_declaration = formatted.find('?>')
		formatted = declaration.group(1) + formatted[generated_declaration + 2:]
	else:
		formatted = (
			formatted.split('\n', 1)[1]
			if formatted.startswith('<?xml') else formatted
		)
	return formatted.rstrip('\n')


def pretty_print(text, path):
	"""Return formatted JSON/XML text, or None when formatting is not useful."""
	extension = _extension(path)
	try:
		if extension in _JSON_EXTENSIONS:
			formatted = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
		elif extension in _XML_EXTENSIONS:
			formatted = _pretty_xml(text)
		else:
			return None
	except (ValueError, TypeError):
		return None
	return formatted if formatted is not None and formatted != text else None


class ViewerFormat:
	"""Own the current text viewer's pretty/original display choice."""
	def __init__(self, view):
		self._view = view
		self._pretty_enabled = True
		self._raw = ''
		self._is_pretty = False

	def display(self, raw):
		self._raw = raw
		formatted = (
			pretty_print(raw, self._view._path)
			if self._pretty_enabled else None
		)
		self._is_pretty = formatted is not None
		return formatted if self._is_pretty else raw

	def is_pretty(self):
		return self._is_pretty

	def actions(self):
		if _extension(self._view._path) not in _JSON_EXTENSIONS | _XML_EXTENSIONS:
			return []
		title = 'Show original' if self._pretty_enabled else 'Pretty print'
		return [(title, self.toggle_pretty, '', 'text_toggle_pretty')]

	def commands(self):
		return {'text_toggle_pretty': self.toggle_pretty}

	def toggle_pretty(self):
		self._pretty_enabled = not self._pretty_enabled
		text = self.display(self._raw)
		from core.textviewer_reload import set_text_preserving_scroll
		set_text_preserving_scroll(self._view, text)
		from core.viewer_status import viewer_status
		if not self._pretty_enabled:
			message = 'Original formatting'
		elif self._is_pretty:
			message = 'Pretty printed'
		else:
			message = 'Could not pretty print %s' % self._format_name()
		viewer_status(self._view._nav.pane, message)

	def _format_name(self):
		return 'JSON' if _extension(self._view._path) in _JSON_EXTENSIONS else 'XML'
