from core.tests.viewer_stubs import FakeSettings, StubPane
from core.viewer_file_ops import (
	after_delete_label, after_file_gone, delete_current, get_close_after_delete,
	rename_current, toggle_close_after_delete,
)
from core.viewer_navigation import ViewerNavigator
from unittest import TestCase
from unittest.mock import patch

class _SettingsTestCase(TestCase):
	def setUp(self):
		self._settings = FakeSettings()
		for name, func in (
			('get_setting', self._settings.get),
			('save_setting', self._settings.save),
		):
			patcher = patch('core.viewer_file_ops.' + name, func)
			patcher.start()
			self.addCleanup(patcher.stop)
		self.pane = StubPane([])
		# Run the off-the-Qt-thread work inline, so assertions see it done.
		patcher = patch('core.viewer_file_ops._in_background', lambda work: work())
		patcher.start()
		self.addCleanup(patcher.stop)

class CloseAfterDeletePersistenceTest(_SettingsTestCase):
	def test_defaults_to_closing_the_viewer(self):
		self.assertIs(True, get_close_after_delete())

	def test_toggle_flips_and_persists(self):
		self.assertIs(False, toggle_close_after_delete(self.pane))
		self.assertIs(False, get_close_after_delete())
		self.assertIs(True, toggle_close_after_delete(self.pane))
		self.assertIs(True, get_close_after_delete())

	def test_label_offers_the_other_mode(self):
		self.assertEqual('Go to next file after deleting', after_delete_label())
		toggle_close_after_delete(self.pane)
		self.assertEqual('Close viewer after deleting', after_delete_label())

class DeleteCurrentTest(_SettingsTestCase):
	def setUp(self):
		super().setUp()
		# advance() classifies by suffix here, so no real files are touched.
		for target, replacement in (
			(
				'core.viewer_navigation._category',
				lambda url: 'image' if url.endswith('.png') else None
			),
			# The same-type key is validated against the viewer registry,
			# which lives on the running app these tests do not have.
			('core.viewer_navigation.get_same_type_only', lambda category: True),
		):
			patcher = patch(target, replacement)
			patcher.start()
			self.addCleanup(patcher.stop)
		self.closed = []
		self.trashed = []

	def _delete(self, pane, confirmed=True):
		with patch(
			'core.viewer_file_ops.confirm_trash', lambda urls: confirmed
		), patch('core.viewer_file_ops.trash', self.trashed.append):
			delete_current(
				pane, pane.get_file_under_cursor(), 'image',
				lambda: self.closed.append(True)
			)

	def test_declining_the_confirmation_does_nothing(self):
		pane = StubPane(['file:///a.png', 'file:///b.png'], cursor=0)
		self._delete(pane, confirmed=False)
		self.assertEqual([], self.trashed)
		self.assertEqual([], self.closed)
		self.assertEqual('file:///a.png', pane.get_file_under_cursor())

	def test_close_mode_closes_the_viewer_and_trashes(self):
		pane = StubPane(['file:///a.png', 'file:///b.png'], cursor=0)
		self._delete(pane)
		self.assertEqual([True], self.closed)
		self.assertEqual([['file:///a.png']], self.trashed)
		self.assertEqual([], pane.commands)

	def test_next_file_mode_advances_and_stays_open(self):
		toggle_close_after_delete(self.pane)
		pane = StubPane(['file:///a.png', 'file:///b.png'], cursor=0)
		self._delete(pane)
		self.assertEqual([], self.closed)
		self.assertEqual('file:///b.png', pane.get_file_under_cursor())
		self.assertEqual(['view_file'], pane.commands)
		self.assertEqual([['file:///a.png']], self.trashed)

	def test_next_file_mode_closes_when_there_is_no_next_file(self):
		toggle_close_after_delete(self.pane)
		pane = StubPane(['file:///a.png'], cursor=0)
		self._delete(pane)
		# advance() put the cursor back on the file we are deleting, so there
		# is nothing left to show.
		self.assertEqual([True], self.closed)
		self.assertEqual([], pane.commands)
		self.assertEqual([['file:///a.png']], self.trashed)

	def test_permanent_rewrite_uses_permanent_confirmation_and_delete(self):
		pane = StubPane(['file:///a.png'], cursor=0)
		pane._rewrite_command = lambda name, args: ('delete_permanently', args)
		with patch(
			'core.viewer_file_ops.confirm_delete', return_value=True,
		) as confirm, \
				patch('core.viewer_file_ops.delete') as delete, \
				patch('core.viewer_file_ops.confirm_trash') as confirm_trash, \
				patch('core.viewer_file_ops.trash') as trash:
			delete_current(pane, 'file:///a.png', 'image', lambda: None)
		confirm.assert_called_once_with(['file:///a.png'])
		delete.assert_called_once_with(['file:///a.png'])
		confirm_trash.assert_not_called()
		trash.assert_not_called()

	def test_unmodified_command_uses_trash_confirmation_and_delete(self):
		pane = StubPane(['file:///a.png'], cursor=0)
		pane._rewrite_command = lambda name, args: (name, args)
		with patch(
			'core.viewer_file_ops.confirm_trash', return_value=True,
		) as confirm, \
				patch('core.viewer_file_ops.trash') as trash, \
				patch('core.viewer_file_ops.confirm_delete') as confirm_delete, \
				patch('core.viewer_file_ops.delete') as delete:
			delete_current(pane, 'file:///a.png', 'image', lambda: None)
		confirm.assert_called_once_with(['file:///a.png'])
		trash.assert_called_once_with(['file:///a.png'])
		confirm_delete.assert_not_called()
		delete.assert_not_called()

class RenameCurrentTest(_SettingsTestCase):
	def _rename(self, prompt_result, on_renamed=None, renamed_to='file:///b.png'):
		pane = StubPane(['file:///a.png'], cursor=0)
		with patch(
			'core.viewer_file_ops.show_prompt', return_value=prompt_result
		), patch(
			'core.viewer_file_ops.rename_to', return_value=renamed_to
		) as rename_to:
			rename_current(pane, 'file:///a.png', on_renamed)
		return rename_to

	def test_cancelled_prompt_renames_nothing(self):
		rename_to = self._rename(('b.png', False))
		rename_to.assert_not_called()

	def test_rejected_name_leaves_the_viewer_alone(self):
		# rename_to returning None means it alerted and did not submit.
		renamed = []
		self._rename(('b.png', True), renamed.append, renamed_to=None)
		self.assertEqual([], renamed)

	def test_accepted_rename_reports_the_new_url(self):
		renamed = []
		rename_to = self._rename(('b.png', True), renamed.append)
		rename_to.assert_called_once_with(
			rename_to.call_args[0][0], 'file:///a.png', 'b.png'
		)
		self.assertEqual(['file:///b.png'], renamed)

	def test_accepted_rename_without_a_callback_does_not_crash(self):
		# The image and video viewers pass no on_renamed.
		rename_to = self._rename(('b.png', True))
		rename_to.assert_called_once()

class AfterFileGoneTest(_SettingsTestCase):
	def setUp(self):
		super().setUp()
		for target, replacement in (
			('core.viewer_navigation._category',
			 lambda url: 'image' if url.endswith('.png') else None),
			('core.viewer_navigation.get_same_type_only', lambda category: True),
		):
			patcher = patch(target, replacement)
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_close_mode_and_empty_folder_close(self):
		closed = []
		pane = StubPane(['file:///b.png'])
		after_file_gone(pane, 'image', lambda: closed.append(True))
		self.assertEqual([True], closed)
		self.assertEqual([], pane.commands)
		toggle_close_after_delete(self.pane)
		after_file_gone(StubPane([]), 'image', lambda: closed.append(True))
		self.assertEqual([True, True], closed)

	def test_next_mode_uses_cursor_or_advances(self):
		toggle_close_after_delete(self.pane)
		closed = []
		pane = StubPane(['file:///b.png'])
		after_file_gone(pane, 'image', lambda: closed.append(True))
		self.assertEqual(['view_file'], pane.commands)
		pane = StubPane(['file:///sub', 'file:///c.png'])
		after_file_gone(pane, 'image', lambda: closed.append(True))
		self.assertEqual(['view_file'], pane.commands)
		self.assertEqual('file:///c.png', pane.get_file_under_cursor())
		self.assertEqual([], closed)

	def test_next_mode_closes_if_no_viewable_file(self):
		toggle_close_after_delete(self.pane)
		closed = []
		pane = StubPane(['file:///sub'])
		after_file_gone(pane, 'image', lambda: closed.append(True))
		self.assertEqual([True], closed)

class BackgroundHopTest(_SettingsTestCase):
	# The pane model's notify_file_added/_removed assert they are not on the
	# main thread, and submit_task runs its task on the calling thread - so a
	# viewer palette action that touched the filesystem directly would change
	# the file but leave the file list stale until a manual reload. Both
	# operations therefore have to hand the filesystem work to _in_background.
	def test_delete_hands_the_filesystem_work_off_the_qt_thread(self):
		backgrounded = []
		pane = StubPane(['file:///a.png'], cursor=0)
		with patch(
			'core.viewer_file_ops.confirm_trash', lambda urls: True
		), patch('core.viewer_file_ops.trash') as trash, patch(
			'core.viewer_file_ops._in_background', backgrounded.append
		):
			delete_current(pane, 'file:///a.png', 'image', lambda: None)
			trash.assert_not_called()
			self.assertEqual(1, len(backgrounded))
			backgrounded[0]()
		trash.assert_called_once_with(['file:///a.png'])

	def test_rename_hands_the_filesystem_work_off_the_qt_thread(self):
		backgrounded = []
		pane = StubPane(['file:///a.png'], cursor=0)
		with patch(
			'core.viewer_file_ops.show_prompt', return_value=('b.png', True)
		), patch('core.viewer_file_ops.rename_to') as rename_to, patch(
			'core.viewer_file_ops._in_background', backgrounded.append
		):
			rename_current(pane, 'file:///a.png')
			rename_to.assert_not_called()
			self.assertEqual(1, len(backgrounded))
			backgrounded[0]()
		rename_to.assert_called_once_with(pane, 'file:///a.png', 'b.png')

	def test_permanent_delete_moves_cursor_before_submitting_background_work(self):
		events = []
		backgrounded = []
		pane = StubPane(['file:///a.png', 'file:///b.png'], cursor=0)
		pane._rewrite_command = lambda name, args: ('delete_permanently', args)
		move_cursor_down = pane.move_cursor_down
		def move_cursor():
			events.append('cursor')
			move_cursor_down()
		pane.move_cursor_down = move_cursor
		def confirm(urls):
			events.append('confirm')
			self.assertEqual('file:///a.png', pane.get_file_under_cursor())
			return True
		with patch('core.viewer_file_ops.get_setting', return_value=False), \
				patch('core.viewer_navigation._category', return_value='image'), \
				patch('core.viewer_navigation.get_same_type_only', return_value=True), \
				patch('core.viewer_file_ops.confirm_delete', side_effect=confirm), \
				patch('core.viewer_file_ops.confirm_trash') as confirm_trash, \
				patch('core.viewer_file_ops.delete') as delete, \
				patch('core.viewer_file_ops.trash') as trash, \
				patch(
					'core.viewer_file_ops._in_background',
					side_effect=lambda work: (
						events.append('submit'), backgrounded.append(work),
					),
				):
			delete_current(pane, 'file:///a.png', 'image', lambda: None)
		self.assertEqual(['confirm', 'cursor', 'submit'], events)
		self.assertEqual('file:///b.png', pane.get_file_under_cursor())
		confirm_trash.assert_not_called()
		delete.assert_not_called()
		trash.assert_not_called()
		backgrounded[0]()
		delete.assert_called_once_with(['file:///a.png'])

class NavigatorEntryTest(TestCase):
	def test_delete_and_rename_are_offered_only_with_an_on_close(self):
		with patch('core.viewer_navigation.get_same_type_only', lambda c: True), \
				patch('core.viewer_file_ops.get_setting', lambda *_a: True):
			pane = StubPane([], aliases={'copy': 'Copy', 'move': 'Move'},
				viewer_commands={'copy', 'move'})
			without = ViewerNavigator(pane=pane, category='image')
			with_close = ViewerNavigator(
				pane=pane, category='image', on_close=lambda: None
			)
			self.assertEqual(
				['Next file', 'Previous file', 'Advance across all file types'],
				[entry[0] for entry in without.actions()]
			)
			with patch('core.viewer_pane_commands.load_json', return_value=[]):
				self.assertEqual(
					['Delete file', 'Rename file…',
					 'Go to next file after deleting', 'Copy', 'Move'],
					[entry[0] for entry in with_close.actions()[3:]]
				)
			self.assertFalse(without.run_pane_shortcut(None))
			self.assertEqual(
				{
					'viewer_next_file', 'viewer_previous_file',
					'viewer_toggle_same_type_advance',
				},
				set(without.commands())
			)
			self.assertEqual(
				{
					'viewer_delete_file', 'viewer_rename_file',
					'viewer_toggle_close_after_delete',
				},
				set(with_close.commands()) - set(without.commands())
			)
