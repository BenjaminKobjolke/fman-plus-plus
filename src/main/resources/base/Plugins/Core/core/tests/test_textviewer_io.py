from core.textviewer_save import write_view
from core.textviewer_io import (
	read_text_for_view, MAX_VIEW_BYTES, is_editable, read_capped,
	load_for_view, is_text_file,
)
from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import patch

import os

def _write_temp_file(test_case, data):
	f = NamedTemporaryFile(delete=False)
	try:
		f.write(data)
	finally:
		f.close()
	test_case.addCleanup(os.remove, f.name)
	return f.name

class ReadTextForViewTest(TestCase):
	def test_reads_small_file_verbatim(self):
		path = _write_temp_file(self, b'hello world')
		self.assertEqual('hello world', read_text_for_view(path))

	def test_replaces_invalid_utf8(self):
		path = _write_temp_file(self, b'valid \xff\xfe invalid')
		text = read_text_for_view(path)
		self.assertIn('valid', text)
		self.assertIn('�', text)

	def test_truncates_oversized_file(self):
		path = _write_temp_file(self, b'x' * (MAX_VIEW_BYTES + 1))
		text = read_text_for_view(path)
		self.assertIn('truncated', text)
		# The truncation notice is appended after exactly the byte cap of
		# 'x' characters (1 byte each), so the body length is predictable:
		self.assertTrue(text.startswith('x' * MAX_VIEW_BYTES))

	def test_does_not_truncate_file_at_exact_cap(self):
		path = _write_temp_file(self, b'x' * MAX_VIEW_BYTES)
		text = read_text_for_view(path)
		self.assertNotIn('truncated', text)
		self.assertEqual('x' * MAX_VIEW_BYTES, text)

	def test_read_capped_reports_truncation(self):
		path = _write_temp_file(self, b'x' * (MAX_VIEW_BYTES + 1))
		data, truncated = read_capped(path)
		self.assertTrue(truncated)
		self.assertEqual(MAX_VIEW_BYTES, len(data))

	def test_read_capped_reports_no_truncation_under_cap(self):
		path = _write_temp_file(self, b'hello')
		data, truncated = read_capped(path)
		self.assertFalse(truncated)
		self.assertEqual(b'hello', data)

class IsEditableTest(TestCase):
	def test_valid_utf8_not_truncated_is_editable(self):
		self.assertTrue(is_editable(b'hello world', truncated=False))

	def test_empty_file_is_editable(self):
		self.assertTrue(is_editable(b'', truncated=False))

	def test_truncated_file_is_not_editable(self):
		# Saving a truncated buffer back would chop off the rest of the real
		# file on disk, so truncation alone disqualifies it regardless of
		# whether the bytes we DID read are valid UTF-8.
		self.assertFalse(is_editable(b'hello world', truncated=True))

	def test_invalid_utf8_is_not_editable(self):
		# read_text_for_view tolerates this via errors='replace', but that
		# replacement is lossy — saving it back would corrupt the original
		# bytes, so strict decoding must be required for editability.
		self.assertFalse(is_editable(b'valid \xff\xfe invalid', truncated=False))

class LoadForViewTest(TestCase):
	def test_small_utf8_file_is_editable(self):
		path = _write_temp_file(self, b'hello world')
		text, editable = load_for_view(path)
		self.assertEqual('hello world', text)
		self.assertTrue(editable)

	def test_oversized_file_is_not_editable(self):
		path = _write_temp_file(self, b'x' * (MAX_VIEW_BYTES + 1))
		text, editable = load_for_view(path)
		self.assertIn('truncated', text)
		self.assertFalse(editable)

	def test_invalid_utf8_file_is_not_editable(self):
		path = _write_temp_file(self, b'valid \xff\xfe invalid')
		text, editable = load_for_view(path)
		self.assertIn('�', text)
		self.assertFalse(editable)

class IsTextFileTest(TestCase):
	def test_plain_text_is_text(self):
		path = _write_temp_file(self, b'hello world')
		self.assertTrue(is_text_file(path))

	def test_null_byte_is_binary(self):
		path = _write_temp_file(self, b'MZ\x00\x00binary stuff')
		self.assertFalse(is_text_file(path))

	def test_missing_file_is_not_text(self):
		self.assertFalse(is_text_file('/no/such/path/does-not-exist'))

class _StubView:
	# write_view only reads the buffer, so it runs against this - the real
	# PaneTextView is a QPlainTextEdit and would need a QApplication.
	def toPlainText(self):
		return 'contents'
	def __init__(self):
		from core.tests.viewer_stubs import StubPane
		self._nav = type('Nav', (), {'pane': StubPane([])})()

class WriteTest(TestCase):
	def test_writes_the_buffer_as_utf8(self):
		path = _write_temp_file(self, b'')
		self.assertTrue(write_view(_StubView(), path))
		with open(path, 'rb') as f:
			self.assertEqual(b'contents', f.read())

	def test_a_failed_write_reports_instead_of_raising(self):
		# A read-only file or a missing directory reaches write_view as OSError.
		# Uncaught, a palette save would traceback and the user would believe
		# it saved.
		missing_dir = os.path.join(_write_temp_file(self, b''), 'nope.txt')
		view = _StubView()
		self.assertFalse(write_view(view, missing_dir))
		message, timeout = view._nav.pane.status_messages[0]
		self.assertIn('Could not save:', message)
		self.assertEqual(3, timeout)
