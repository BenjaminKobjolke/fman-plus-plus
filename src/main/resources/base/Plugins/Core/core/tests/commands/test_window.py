from core.commands.window import _format_window_title
from unittest import TestCase

class FormatWindowTitleTest(TestCase):
	def test_no_paths(self):
		self.assertEqual('fman++', _format_window_title([]))
	def test_blank_paths_skipped(self):
		self.assertEqual('fman++', _format_window_title(['', '']))
	def test_one_path(self):
		self.assertEqual(
			'test - fman++',
			_format_window_title(['C:\\test'])
		)
	def test_two_paths(self):
		self.assertEqual(
			'test | dir - fman++',
			_format_window_title(['C:\\test', 'D:\\other\\dir'])
		)
	def test_drive_root_keeps_full_path(self):
		self.assertEqual('C:\\ - fman++', _format_window_title(['C:\\']))
	def test_non_file_urls_use_their_last_segment_when_present(self):
		self.assertEqual(
			'inner - fman++',
			_format_window_title(['zip://C:/a.zip/inner'])
		)
	def test_non_file_urls_without_a_folder_segment_keep_full_text(self):
		self.assertEqual(
			'network:// - fman++', _format_window_title(['network://'])
		)
	def test_trailing_separator_is_ignored(self):
		self.assertEqual(
			'other - fman++', _format_window_title(['D:\\other\\'])
		)
