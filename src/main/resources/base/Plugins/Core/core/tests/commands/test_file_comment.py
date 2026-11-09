from core.commands.file_comment import EditComment
from unittest import TestCase
from unittest.mock import Mock, call, patch


class EditCommentTest(TestCase):
	def setUp(self):
		self.window = Mock()
		self.pane = Mock(window=self.window)
		self.command = EditComment(self.pane)

	def test_saves_comment_for_cursor_file_and_refreshes_both_panes(self):
		urls = ['file:///media/film.mkv']
		self.pane.get_selected_files.return_value = []
		self.pane.get_file_under_cursor.return_value = urls[0]
		panes = [Mock(), Mock()]
		self.window.get_panes.return_value = panes
		with patch('core.commands.file_comment.get_comment', return_value=None), \
				patch(
					'core.commands.file_comment.show_text_input', return_value='plot'
				), \
				patch('core.commands.file_comment.set_comment') as set_comment, \
				patch('core.commands.file_comment._apply_column_visibility') as apply, \
				patch('core.commands.file_comment.reload_panes') as reload:
			self.command()

		set_comment.assert_called_once_with(urls, 'plot')
		apply.assert_has_calls([call(pane) for pane in panes])
		reload.assert_called_once_with(self.window)

	def test_prefills_shared_comment_and_uses_multi_file_title(self):
		urls = ['file:///media/a.mkv', 'file:///media/b.mkv']
		self.command.get_chosen_files = Mock(return_value=urls)
		with patch(
			'core.commands.file_comment.get_comment', return_value='rating: 5'
		), \
				patch(
					'core.commands.file_comment.show_text_input', return_value=None
				) as editor:
			self.command()
		self.assertEqual('Comment for 2 files', editor.call_args.args[0])
		self.assertEqual('rating: 5', editor.call_args.args[1])

	def test_does_not_prefill_when_comments_differ(self):
		urls = ['file:///media/a.mkv', 'file:///media/b.mkv']
		self.command.get_chosen_files = Mock(return_value=urls)
		with patch(
			'core.commands.file_comment.get_comment', side_effect=['one', 'two']
		), \
				patch(
					'core.commands.file_comment.show_text_input', return_value=None
				) as editor:
			self.command()
		self.assertEqual('', editor.call_args.args[1])

	def test_single_file_title_names_the_file(self):
		self.command.get_chosen_files = Mock(return_value=['file:///media/film.mkv'])
		with patch('core.commands.file_comment.get_comment', return_value=None), \
				patch(
					'core.commands.file_comment.show_text_input', return_value=None
				) as editor:
			self.command()
		self.assertEqual('Comment for film.mkv', editor.call_args.args[0])

	def test_cancel_does_not_save_or_reload(self):
		self.command.get_chosen_files = Mock(return_value=['file:///media/a.mkv'])
		with patch('core.commands.file_comment.get_comment', return_value=None), \
				patch(
					'core.commands.file_comment.show_text_input', return_value=None
				), \
				patch('core.commands.file_comment.set_comment') as save, \
				patch('core.commands.file_comment.reload_panes') as reload:
			self.command()
		save.assert_not_called()
		reload.assert_not_called()

	def test_non_local_files_show_status_and_skip_editor(self):
		self.command.get_chosen_files = Mock(return_value=['zip://archive/a.mkv'])
		with patch('core.commands.file_comment.show_status_message') as status, \
				patch('core.commands.file_comment.show_text_input') as editor:
			self.command()
		status.assert_called_once()
		editor.assert_not_called()

	def test_no_chosen_files_shows_alert(self):
		self.command.get_chosen_files = Mock(return_value=[])
		with patch('core.commands.file_comment.show_alert') as alert, \
				patch('core.commands.file_comment.show_text_input') as editor:
			self.command()
		alert.assert_called_once()
		editor.assert_not_called()

	def test_save_error_shows_alert_and_does_not_refresh(self):
		self.command.get_chosen_files = Mock(return_value=['file:///media/a.mkv'])
		self.window.get_panes.return_value = []
		with patch('core.commands.file_comment.get_comment', return_value=None), \
				patch(
					'core.commands.file_comment.show_text_input', return_value='note'
				), \
				patch(
					'core.commands.file_comment.set_comment',
					side_effect=OSError('read-only')
				), \
				patch('core.commands.file_comment.show_alert') as alert, \
				patch('core.commands.file_comment.reload_panes') as reload:
			self.command()
		alert.assert_called_once()
		reload.assert_not_called()
