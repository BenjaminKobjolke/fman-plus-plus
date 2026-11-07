from fman.impl.shell_change_notices import ShellChangeBatch, ShellChangeListener
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock, patch


_APP = QApplication.instance() or QApplication([])


class ShellChangeBatchTest(TestCase):

	def test_batches_changed_items_by_parent_folder(self):
		batch = ShellChangeBatch()

		batch.add(r'C:\work\one.txt')
		batch.add(r'C:\work\two.txt')
		batch.add(r'C:\other\three.txt')

		self.assertEqual(
			('file://C:/other', 'file://C:/work'), batch.flush()
		)
		self.assertEqual((), batch.flush())

	def test_updated_directory_refreshes_itself_and_its_parent(self):
		batch = ShellChangeBatch()

		batch.add(r'C:\work\subfolder', include_path=True)

		self.assertEqual(
			('file://C:/work', 'file://C:/work/subfolder'), batch.flush()
		)

	def test_flush_clears_a_batch_before_the_next_notice(self):
		batch = ShellChangeBatch()

		batch.add(r'C:\work\one.txt')
		self.assertEqual(('file://C:/work',), batch.flush())
		batch.add(r'C:\work\two.txt')

		self.assertEqual(('file://C:/work',), batch.flush())


class ShellChangeListenerTest(TestCase):

	def test_debounced_flush_invalidates_icons_and_reloads_matching_panes(self):
		pane = Mock()
		pane.get_location.return_value = 'file://C:/WORK'
		other_pane = Mock()
		other_pane.get_location.return_value = 'file://C:/elsewhere'
		window = Mock()
		window.get_panes.return_value = [pane, other_pane]
		source = _NotificationSource()
		listener = ShellChangeListener(window, lambda: True, source)

		try:
			source.notify([r'C:\work\one.txt', r'C:\work\two.txt'])
			self.assertEqual(300, listener._timer.interval())
			with patch('fman.impl.shell_change_notices.invalidate_icons') \
				as invalidate_icons:
				listener._flush()
			invalidate_icons.assert_called_once_with()
			pane.reload.assert_called_once_with()
			other_pane.reload.assert_not_called()
		finally:
			listener.close()

	def test_disabled_overlays_do_not_refresh_panes(self):
		pane = Mock()
		pane.get_location.return_value = 'file://C:/work'
		window = Mock()
		window.get_panes.return_value = [pane]
		listener = ShellChangeListener(
			window, lambda: False, _NotificationSource()
		)

		try:
			listener._on_changed_paths([r'C:\work\one.txt'])
			with patch('fman.impl.shell_change_notices.invalidate_icons') \
				as invalidate_icons:
				listener._flush()
			invalidate_icons.assert_not_called()
			pane.reload.assert_not_called()
		finally:
			listener.close()


class _NotificationSource:
	def set_callback(self, callback):
		self._callback = callback

	def notify(self, paths, event_id=0):
		self._callback(paths, event_id)

	def close(self):
		pass
