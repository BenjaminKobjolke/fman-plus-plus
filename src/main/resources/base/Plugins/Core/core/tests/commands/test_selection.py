from core.commands import selection
from core.tests.commands import FakePane
from unittest import TestCase
from unittest.mock import patch


class SelectionMaskTest(TestCase):
	def test_matches_includes_exclusions_and_folder_patterns(self):
		cases = (
			('*.jpg', 'A.JPG', False, True),
			('*.jpg;*.png', 'a.PNG', False, True),
			('*.*', 'README', False, True),
			('*', 'README', False, True),
			('*.jpg | thumb*', 'thumb1.jpg', False, False),
			('| *.bak', 'notes.txt', False, True),
			('| *.bak', 'old.bak', False, False),
			('src' + chr(92), 'src', True, True),
			('src' + chr(92), 'src', False, False),
			('*' + chr(92), 'folder', True, True),
			('*' + chr(92) + ' | .git' + chr(92), '.git', True, False),
			('', 'a.txt', False, False),
			(' *.jpg ; *.png | thumb* ', 'photo.jpg', False, True),
		)
		for mask, name, is_folder, expected in cases:
			with self.subTest(mask=mask, name=name, is_folder=is_folder):
				self.assertEqual(
					expected,
					selection.SelectionMask.parse(mask).matches(name, is_folder),
				)


class MaskHistoryTest(TestCase):
	def test_remember_moves_mask_to_front_without_duplicates_and_caps_at_20(self):
		history = ['mask %d' % i for i in range(20)]
		with patch.object(selection, 'get_setting', return_value=history), \
				patch.object(selection, 'save_setting') as save_setting:
			selection.remember_mask('mask 5')
		history = save_setting.call_args.args[2]
		self.assertEqual('selection_mask_history', save_setting.call_args.args[1])
		self.assertEqual('mask 5', history[0])
		self.assertEqual(20, len(history))
		self.assertEqual(1, history.count('mask 5'))

	def test_empty_mask_is_not_saved_and_non_list_history_is_empty(self):
		with patch.object(selection, 'get_setting', return_value='bad'):
			self.assertEqual([], selection.get_mask_history())
		with patch.object(selection, 'get_setting', return_value=[]), \
				patch.object(selection, 'save_setting') as save_setting:
			selection.remember_mask('  ')
		save_setting.assert_not_called()


class SelectionPane(FakePane):
	def __init__(self, cursor=None):
		super().__init__(url=cursor)
		self.path = 'file:///here'
		self.selected = []
		self.deselected = []
		self.status_messages = []
	def get_path(self):
		return self.path
	def select(self, urls):
		self.selected.extend(urls)
	def deselect(self, urls):
		self.deselected.extend(urls)
	def show_status_message(self, message, timeout_secs=None):
		self.status_messages.append((message, timeout_secs))


class SelectionCommandsTest(TestCase):
	def setUp(self):
		self.pane = SelectionPane()
		self.entries = {
			'a.jpg': False, 'thumb1.jpg': False, 'b.txt': False, 'dir': True,
		}

	def _filesystem(self):
		return patch.object(selection, 'iterdir', return_value=list(self.entries)), \
			patch.object(
				selection,
				'is_dir',
				side_effect=lambda url: self.entries[url.rsplit('/', 1)[-1].lower()],
			)

	def test_group_with_mask_skips_dialog_and_selects_matching_file(self):
		with self._filesystem()[0], self._filesystem()[1], \
				patch.object(selection, 'show_quicksearch') as dialog:
			selection.SelectGroup(self.pane)(mask='*.jpg | thumb*')
		dialog.assert_not_called()
		self.assertEqual(['file:///here/a.jpg'], self.pane.selected)

	def test_dialog_uses_typed_or_picked_mask_and_remembers_it(self):
		for result, expected in [
			(('*.jpg', None), '*.jpg'),
			(('typed', '*.png'), '*.png'),
		]:
			with self.subTest(result=result):
				self.pane.selected = []
				with self._filesystem()[0], self._filesystem()[1], \
						patch.object(
							selection, 'show_quicksearch', return_value=result
						), \
						patch.object(selection, 'remember_mask') as remember:
					selection.SelectGroup(self.pane)()
				remember.assert_called_once_with(expected)
				self.assertEqual(
					['file:///here/a.jpg', 'file:///here/thumb1.jpg']
					if expected == '*.jpg' else [],
					self.pane.selected,
				)

	def test_cancelled_dialog_does_nothing(self):
		with patch.object(selection, 'show_quicksearch', return_value=None), \
				patch.object(selection, 'iterdir') as iterdir:
			selection.SelectGroup(self.pane)()
		iterdir.assert_not_called()
		self.assertEqual([], self.pane.selected)

	def test_deselect_group_only_deselects_matching_files(self):
		with self._filesystem()[0], self._filesystem()[1]:
			selection.DeselectGroup(self.pane)(mask='*.jpg')
		self.assertEqual(
			['file:///here/a.jpg', 'file:///here/thumb1.jpg'],
			self.pane.deselected,
		)

	def test_quicksearch_items_put_typed_text_before_filtered_history(self):
		with patch.object(
			selection, 'get_mask_history', return_value=['*.jpg', '*.png', '*.jpeg']
		):
			items = list(selection._mask_items('j'))
		self.assertEqual(['j', '*.jpg', '*.jpeg'], [item.title for item in items])

	def test_empty_quicksearch_offers_history_or_default(self):
		with patch.object(
			selection, 'get_mask_history', return_value=['*.png', '*.jpg']
		):
			self.assertEqual(
				['*.png', '*.jpg'], [i.title for i in selection._mask_items('')]
			)
		with patch.object(selection, 'get_mask_history', return_value=[]):
			self.assertEqual(['*.*'], [i.title for i in selection._mask_items('')])

	def test_same_extension_selects_and_deselects_matching_files(self):
		self.pane.get_file_under_cursor = lambda: 'file:///here/a.JPG'
		with self._filesystem()[0], self._filesystem()[1]:
			selection.SelectSameExtension(self.pane)()
		with self._filesystem()[0], self._filesystem()[1]:
			selection.DeselectSameExtension(self.pane)()
		self.assertEqual(
			['file:///here/a.jpg', 'file:///here/thumb1.jpg'], self.pane.selected
		)
		self.assertEqual(self.pane.selected, self.pane.deselected)

	def test_same_extension_requires_a_cursor_file(self):
		for cursor in (None, 'file:///here/dir'):
			with self.subTest(cursor=cursor):
				self.pane.get_file_under_cursor = lambda: cursor
				with patch.object(selection, 'is_dir', return_value=True), \
						patch.object(selection, 'iterdir') as iterdir, \
						patch.object(selection, 'show_status_message') as status:
					selection.SelectSameExtension(self.pane)()
				iterdir.assert_not_called()
				status.assert_called_once_with(
					'Put the cursor on a file to use its extension.', timeout_secs=3
				)
