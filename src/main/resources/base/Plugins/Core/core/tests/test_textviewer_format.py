from unittest import TestCase
from unittest.mock import patch

from core.textviewer_format import ViewerFormat, pretty_print


class PrettyPrintTest(TestCase):
	def test_formats_json_with_two_space_indentation(self):
		self.assertEqual(
			'{\n  "a": [\n    1,\n    2\n  ]\n}',
			pretty_print('{"a":[1,2]}', 'file.JSON')
		)

	def test_keeps_non_ascii_json_characters(self):
		self.assertEqual(
			'{\n  "text": "café"\n}',
			pretty_print('{"text":"café"}', 'a.json')
		)

	def test_invalid_unknown_and_missing_path_return_none(self):
		self.assertIsNone(pretty_print('{', 'a.json'))
		self.assertIsNone(pretty_print('{}', 'a.txt'))
		self.assertIsNone(pretty_print('{}', None))

	def test_already_pretty_json_returns_none(self):
		self.assertIsNone(pretty_print('{\n  "a": 1\n}', 'a.json'))

	def test_formats_xml_and_preserves_only_an_existing_declaration(self):
		self.assertEqual(
			'<root>\n  <child/>\n</root>',
			pretty_print('<root><child/></root>', 'a.xml')
		)
		with_declaration = '<?xml version="1.0"?><root><child/></root>'
		formatted = pretty_print(with_declaration, 'a.xml')
		self.assertTrue(formatted.startswith('<?xml version="1.0"?>\n'))
		without_declaration = pretty_print('<root><child/></root>', 'a.xml')
		self.assertNotIn('<?xml', without_declaration)

	def test_xml_whitespace_does_not_create_blank_lines(self):
		self.assertIsNone(pretty_print('<root>\n  <child/>\n</root>', 'a.xml'))

	def test_invalid_xml_returns_none(self):
		self.assertIsNone(pretty_print('<root>', 'a.xml'))


class _FakeView:
	_path = 'a.json'

	class _Nav:
		pane = None

	_nav = _Nav()


class ViewerFormatTest(TestCase):
	def test_display_formats_until_show_original_is_selected(self):
		view = _FakeView()
		formatter = ViewerFormat(view)
		raw = '{"a":1}'
		self.assertEqual('{\n  "a": 1\n}', formatter.display(raw))
		self.assertTrue(formatter.is_pretty())

		with patch('core.textviewer_reload.set_text_preserving_scroll') as set_text:
			with patch('core.viewer_status.viewer_status'):
				formatter.toggle_pretty()
		self.assertEqual((view, raw), set_text.call_args.args)
		self.assertFalse(formatter.is_pretty())
		self.assertEqual(raw, formatter.display(raw))

	def test_toggle_action_names_follow_the_current_mode(self):
		formatter = ViewerFormat(_FakeView())
		self.assertEqual('Show original', formatter.actions()[0][0])
		with patch('core.textviewer_reload.set_text_preserving_scroll'):
			with patch('core.viewer_status.viewer_status'):
				formatter.toggle_pretty()
		self.assertEqual('Pretty print', formatter.actions()[0][0])
