from core import descript_ion
from core.descript_ion import CommentFile
from fman.url import as_url
import os
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch


class CommentFileTest(TestCase):
	def test_parses_entries_and_preserves_unrelated_lines(self):
		comments = CommentFile(
			'plain.txt one line\r\n"file name.txt" first\\nsecond\x04Â\r\n'
			'untouchedline', 'utf-8'
		)
		self.assertEqual('one line', comments.get('plain.txt'))
		self.assertEqual('first\nsecond', comments.get('file name.txt'))
		self.assertEqual(
			[('plain.txt', 'one line'), ('file name.txt', 'first\nsecond')],
			comments.entries(),
		)
		comments.set('file name.txt', 'changed\ncomment')
		self.assertEqual(
			'plain.txt one line\r\n"file name.txt" changed\\ncomment\x04Â\r\n'
			'untouchedline',
			comments.to_text(),
		)

	def test_remove_and_empty_comment_remove_entry(self):
		comments = CommentFile('a.txt alpha\r\nb.txt beta', 'utf-8')
		comments.remove('a.txt')
		comments.set('b.txt', '')
		self.assertEqual([], comments.entries())
		self.assertEqual('', comments.to_text())

	def test_quotes_names_with_spaces(self):
		comments = CommentFile('', 'utf-8')
		comments.set('two words.txt', 'comment')
		comments.set('plain.txt', 'comment')
		self.assertEqual(
			'"two words.txt" comment\r\nplain.txt comment', comments.to_text()
		)

	def test_windows_name_matching_is_case_insensitive(self):
		with patch('core.descript_ion.PLATFORM', 'Windows'):
			comments = CommentFile('File.TXT note', 'utf-8')
			self.assertEqual('note', comments.get('file.txt'))
			comments.set('file.txt', 'updated')
			self.assertEqual('File.TXT updated', comments.to_text())


class CommentFileUrlsTest(TestCase):
	def setUp(self):
		self._temporary_directory = TemporaryDirectory()
		self.addCleanup(self._temporary_directory.cleanup)
		self.directory = self._temporary_directory.name
		self.file_url = as_url(self.directory + '/video.mkv')
		self.other_url = as_url(self.directory + '/other.mkv')

	def test_reads_and_writes_bom_utf8_and_refreshes_cache(self):
		descript_path = self.directory + '/descript.ion'
		with open(descript_path, 'wb') as file:
			file.write(b'\xef\xbb\xbfvideo.mkv hello')
		self.assertEqual('hello', descript_ion.get_comment(self.file_url))
		descript_ion.set_comment([self.file_url], 'café')
		with open(descript_path, 'rb') as file:
			self.assertTrue(file.read().startswith(b'\xef\xbb\xbf'))
		self.assertEqual('café', descript_ion.get_comment(self.file_url))
		with open(descript_path, 'wb') as file:
			file.write(b'video.mkv changed externally')
		self.assertEqual('changed externally', descript_ion.get_comment(self.file_url))

	def test_falls_back_to_ansi_and_switches_to_bom_for_unencodable_text(self):
		descript_path = self.directory + '/descript.ion'
		with open(descript_path, 'wb') as file:
			file.write(b'video.mkv caf\xe9')
		self.assertEqual('café', descript_ion.get_comment(self.file_url))
		descript_ion.set_comment([self.file_url], '雪')
		with open(descript_path, 'rb') as file:
			data = file.read()
		self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
		self.assertIn('雪'.encode('utf-8'), data)

	def test_empty_comment_removes_entry_and_last_entry_deletes_file(self):
		descript_ion.set_comment([self.file_url], 'hello')
		descript_path = self.directory + '/descript.ion'
		self.assertTrue(descript_ion.has_comments(as_url(self.directory)))
		descript_ion.set_comment([self.file_url], '')
		self.assertFalse(descript_ion.has_comments(as_url(self.directory)))
		self.assertFalse(os.path.exists(descript_path))

	def test_copy_move_remove_and_restore_comments(self):
		descript_ion.set_comment([self.file_url], 'a note')
		descript_ion.copy_comments([(self.file_url, self.other_url)])
		self.assertEqual('a note', descript_ion.get_comment(self.other_url))
		descript_ion.move_comments([(self.other_url, self.file_url)])
		self.assertIsNone(descript_ion.get_comment(self.other_url))
		self.assertEqual('a note', descript_ion.get_comment(self.file_url))
		removed = descript_ion.remove_comments([self.file_url])
		self.assertEqual([(self.file_url, 'a note')], removed)
		self.assertIsNone(descript_ion.get_comment(self.file_url))
		descript_ion.restore_comments(removed)
		self.assertEqual('a note', descript_ion.get_comment(self.file_url))

	def test_move_ignores_non_file_destinations_and_case_only_renames(self):
		descript_ion.set_comment([self.file_url], 'a note')
		descript_ion.move_comments([
			(self.file_url, 'zip://archive.zip/video.mkv'),
		])
		self.assertEqual('a note', descript_ion.get_comment(self.file_url))
		case_only_destination = as_url(self.directory + '/VIDEO.mkv')
		with patch('core.descript_ion.PLATFORM', 'Windows'):
			descript_ion.move_comments([
				(self.file_url, case_only_destination),
			])
		self.assertEqual('a note', descript_ion.get_comment(self.file_url))

	def test_non_file_urls_are_ignored(self):
		self.assertIsNone(descript_ion.get_comment('zip://archive.zip/video.mkv'))
		self.assertFalse(descript_ion.has_comments('zip://archive.zip'))
		descript_ion.set_comment(['zip://archive.zip/video.mkv'], 'ignored')
		descript_ion.copy_comments([
			('zip://archive.zip/video.mkv', self.file_url),
		])
		self.assertIsNone(descript_ion.get_comment(self.file_url))
