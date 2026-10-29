from core.commands.archives import ArchiveOpenListener, _get_handler_for_archive
from json import load
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

class GetHandlerForArchiveTest(TestCase):

	"""
	The suffix -> scheme lookup behind "Enter opens a .zip like a folder".
	Handlers are tried longest suffix first, so '.tar.gz' cannot be stolen by
	a plugin that registered plain '.gz'.
	"""

	_HANDLERS = {
		'.zip': 'zip://',
		'.gz': 'gz://',
		'.tar.gz': 'tar.gz://',
		'.rar': 'rar://',
	}

	def test_matches_a_registered_suffix(self):
		self.assertEqual('zip://', self._handler('archive.zip'))
	def test_longest_suffix_wins(self):
		self.assertEqual('tar.gz://', self._handler('archive.tar.gz'))
	def test_is_case_insensitive(self):
		self.assertEqual('zip://', self._handler('ARCHIVE.ZIP'))
	def test_enter_on_rar_opens_rar_filesystem(self):
		with open(Path(__file__).parents[3] / 'Core Settings.json') as settings_file:
			settings = load(settings_file)
		with patch(
			'core.commands.archives.load_json',
			return_value=settings
		), patch('core.commands.archives.is_dir', return_value=False):
			result = ArchiveOpenListener(None).on_command(
				'open_file', {'url': 'file://C:/archives/x.RAR'}
			)
		self.assertEqual(
			('open_directory', {'url': 'rar://C:/archives/x.RAR'}), result
		)
	def test_xz_files_use_the_7zip_filesystem(self):
		with open(Path(__file__).parents[3] / 'Core Settings.json') as settings_file:
			settings = load(settings_file)
		with patch('core.commands.archives.load_json', return_value=settings):
			self.assertEqual('7z://', _get_handler_for_archive('archive.xz'))
	def test_unknown_suffix_has_no_handler(self):
		self.assertIsNone(self._handler('notes.txt'))
	def test_no_handlers_configured(self):
		self.assertIsNone(self._handler('archive.zip', handlers={}))
	def _handler(self, file_name, handlers=None):
		if handlers is None:
			handlers = self._HANDLERS
		with patch(
			'core.commands.archives.load_json',
			return_value={'archive_handlers': handlers}
		):
			return _get_handler_for_archive(file_name)
