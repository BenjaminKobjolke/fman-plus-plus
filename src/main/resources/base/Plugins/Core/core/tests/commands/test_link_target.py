from core.commands import link_target
from core.tests.commands import FakePane
from fman import NO, PLATFORM, YES
from fman.url import as_url
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

import os


class EditLinkTargetTest(TestCase):
	def setUp(self):
		self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
		self.first_target = self.root / 'first'
		self.second_target = self.root / 'second'
		self.first_target.mkdir()
		self.second_target.mkdir()
		self.link = self.root / 'link'
		self.url = as_url(str(self.link))
		self.pane = FakePane(url=self.url)
		self.command = link_target.EditLinkTarget(self.pane)
		patcher = patch.object(link_target, 'notify_file_changed', autospec=True)
		patcher.start()
		self.addCleanup(patcher.stop)

	def make_symlink(self, target, link=None, is_dir=False):
		link = link or self.link
		try:
			os.symlink(str(target), str(link), target_is_directory=is_dir)
		except OSError as error:
			self.skipTest('symlink creation is not permitted: %s' % error)

	def read_target(self):
		target = os.readlink(self.link)
		return target[4:] if target.startswith('\\\\?\\') else target

	def test_visibility_for_symlink_and_rejects_other_items(self):
		self.make_symlink(self.first_target, is_dir=True)
		self.assertTrue(self.command.is_visible())
		self.link.unlink()
		plain_file = self.root / 'plain.txt'
		plain_file.touch()
		self.pane._url = as_url(str(plain_file))
		self.assertFalse(self.command.is_visible())
		self.pane._url = as_url(str(self.first_target))
		self.assertFalse(self.command.is_visible())
		self.pane._url = 'zip://archive/link'
		self.assertFalse(self.command.is_visible())
		self.pane._url = None
		self.assertFalse(self.command.is_visible())

	def test_retarget_keeps_link_name_and_leaves_no_temporary_link(self):
		self.make_symlink(self.first_target, is_dir=True)
		with patch.object(
				link_target, 'show_input', return_value=str(self.second_target)
		), \
				patch.object(link_target, 'show_alert') as alert:
			self.command()
		self.assertEqual(str(self.second_target), self.read_target())
		self.assertTrue(self.link.is_symlink())
		self.assertEqual(3, len(os.listdir(self.root)))
		alert.assert_not_called()

	def test_directory_symlink_stays_a_directory_link(self):
		self.make_symlink(self.first_target, is_dir=True)
		with patch.object(
				link_target, 'show_input', return_value=str(self.second_target)
	):
			self.command()
		self.assertTrue(os.path.isdir(self.link))
		self.assertTrue(self.link.is_symlink())

	def test_missing_target_no_keeps_old_target_and_yes_saves(self):
		self.make_symlink(self.first_target, is_dir=True)
		missing = self.root / 'missing'
		with patch.object(link_target, 'show_input', return_value=str(missing)), \
				patch.object(link_target, 'show_alert', return_value=NO) as alert:
			self.command()
		self.assertEqual(str(self.first_target), self.read_target())
		alert.assert_called_once()
		with patch.object(link_target, 'show_input', return_value=str(missing)), \
				patch.object(link_target, 'show_alert', return_value=YES):
			self.command()
		self.assertEqual(str(missing), self.read_target())

	def test_cancel_empty_and_unchanged_input_do_nothing(self):
		self.make_symlink(self.first_target, is_dir=True)
		for value in (None, '', str(self.first_target)):
			with self.subTest(value=value), \
					patch.object(link_target, 'show_input', return_value=value), \
					patch.object(link_target, 'show_alert') as alert:
				self.command()
				self.assertEqual(str(self.first_target), self.read_target())
				alert.assert_not_called()

	def test_create_failure_keeps_old_link_and_shows_error(self):
		self.make_symlink(self.first_target, is_dir=True)
		with patch.object(
				link_target, 'show_input', return_value=str(self.second_target)
		), \
				patch.object(
					link_target.os, 'symlink', side_effect=OSError('denied')
				), \
				patch.object(link_target, 'show_alert') as alert:
			self.command()
		self.assertEqual(str(self.first_target), self.read_target())
		self.assertEqual(3, len(os.listdir(self.root)))
		alert.assert_called_once()

	def test_failed_swap_restores_old_link(self):
		self.make_symlink(self.first_target, is_dir=True)
		real_rename = os.rename
		install_attempts = 0
		def fail_first_install(source, destination):
			nonlocal install_attempts
			if destination == str(self.link) and source != str(self.link):
				install_attempts += 1
				if install_attempts == 1:
					raise OSError('swap denied')
			return real_rename(source, destination)
		with patch.object(
				link_target, 'show_input', return_value=str(self.second_target)
		), \
				patch.object(
					link_target.os, 'rename', side_effect=fail_first_install
				), \
				patch.object(link_target, 'show_alert'):
			self.command()
		self.assertEqual(str(self.first_target), self.read_target())
		self.assertEqual(3, len(os.listdir(self.root)))

	@skipUnless(PLATFORM == 'Windows', 'junctions are a Windows concept')
	def test_junction_is_visible_and_retargeted_without_extended_prefix(self):
		import _winapi
		_winapi.CreateJunction(str(self.first_target), str(self.link))
		self.assertTrue(self.command.is_visible())
		with patch.object(
				link_target, 'show_input', return_value=str(self.second_target)
		) as show_input:
			self.command()
		self.assertTrue(os.path.isjunction(self.link))
		self.assertEqual(
			str(self.second_target),
			os.readlink(self.link).removeprefix('\\\\?\\')
		)
		self.assertEqual(
			str(self.first_target), show_input.call_args.args[1]
		)

	@skipUnless(PLATFORM == 'Windows', 'Windows shortcuts are Windows only')
	def test_shortcut_retarget_preserves_arguments(self):
		import win32com.client
		shortcut_path = self.root / 'link.LNK'
		shortcut = win32com.client.Dispatch(
			'WScript.Shell'
		).CreateShortCut(str(shortcut_path))
		shortcut.TargetPath = str(self.first_target)
		shortcut.Arguments = '--keep-argument'
		shortcut.Save()
		self.pane._url = as_url(str(shortcut_path))
		self.command = link_target.EditLinkTarget(self.pane)
		with patch.object(
				link_target, 'show_input', return_value=str(self.second_target)
		):
			self.command()
		updated = win32com.client.Dispatch(
			'WScript.Shell'
		).CreateShortCut(str(shortcut_path))
		self.assertEqual(str(self.second_target), updated.TargetPath)
		self.assertEqual('--keep-argument', updated.Arguments)

	@skipUnless(PLATFORM == 'Windows', 'shortcuts are Windows only')
	def test_shortcut_is_visible_case_insensitively(self):
		shortcut_path = self.root / 'example.LNK'
		shortcut_path.touch()
		self.pane._url = as_url(str(shortcut_path))
		self.assertTrue(self.command.is_visible())
