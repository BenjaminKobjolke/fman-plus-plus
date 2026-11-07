from fman.impl.plugins.builtin import BuiltinPlugin
from json import load
from os.path import dirname, join
from unittest import TestCase
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


class BuiltinPaneStatusCommandsTest(TestCase):

	def test_show_transfer_queue_command_is_registered_and_opens_the_queue(self):
		commands = self._application_commands()
		self.assertIn('ShowTransferQueue', commands)
		window = MagicMock()
		commands['ShowTransferQueue'](SimpleNamespace(_widget=window))()
		window.show_transfer_queue.assert_called_once_with()

	def test_run_in_transfer_queue_delegates_to_the_main_window_queue(self):
		from fman import run_in_transfer_queue
		work = object()
		queue = MagicMock()
		queue.run.return_value = False
		with patch('fman._get_ui') as get_ui:
			get_ui.return_value.get_transfer_queue.return_value = queue
			self.assertFalse(run_in_transfer_queue('Copy item', work))
		queue.run.assert_called_once_with('Copy item', work)

	def test_right_button_selection_toggle_is_registered_and_shows_message(self):
		window_chrome = MagicMock()
		commands = self._application_commands(window_chrome=window_chrome)
		self.assertIn('ToggleRightButtonSelection', commands)
		window_chrome.right_button_selection.toggle.return_value = 'Selection on.'
		window = SimpleNamespace(_widget=MagicMock())
		commands['ToggleRightButtonSelection'](window)()
		window_chrome.right_button_selection.toggle.assert_called_once_with(
			window._widget)
		window._widget.show_status_message.assert_called_once_with('Selection on.')

	def test_registers_both_pane_status_commands_on_every_platform(self):
		commands = []
		args = [MagicMock() for _ in range(7)]
		window_chrome = MagicMock()
		scripting_control = MagicMock()
		with patch.object(
			BuiltinPlugin, '_register_application_command',
			side_effect=commands.append
		), patch.object(BuiltinPlugin, '_register_directory_pane_command'), \
			patch.object(BuiltinPlugin, '_register_file_system'), \
			patch.object(BuiltinPlugin, '_register_column'), \
			patch('fman.impl.plugins.builtin.is_mac', return_value=False):
			BuiltinPlugin(None, None, None, window_chrome, scripting_control,
				None, *args)

		by_name = {command.__name__: command for command in commands}
		self.assertIn('TogglePaneStatusLines', by_name)
		self.assertIn('TogglePaneMessagesInStatusBar', by_name)

		window = MagicMock()
		by_name['TogglePaneStatusLines'](window)()
		window_chrome.pane_status.toggle_lines_visible.assert_called_once_with(
			window._widget)

		by_name['TogglePaneMessagesInStatusBar'](window)()
		window_chrome.pane_status.toggle_in_status_bar.assert_called_once_with(
			window._widget)

	def test_command_keywords_are_registered(self):
		path = join(
			dirname(dirname(dirname(dirname(dirname(dirname(__file__)))))),
			'src', 'main', 'resources', 'base', 'Plugins', 'Core',
			'Command Keywords.json')
		with open(path, encoding='utf-8') as file:
			keywords = load(file)
		self.assertEqual(
			['pane status lines', 'pane status bar', 'show pane status'],
			keywords['toggle_pane_status_lines'])
		self.assertEqual(
			['pane messages in status bar', 'copy pane messages',
			 'status bar pane messages'],
			keywords['toggle_pane_messages_in_status_bar'])

	def test_resume_command_restores_the_only_minimized_dialog_directly(self):
		commands = self._application_commands()
		dialog = object()
		tool_windows = _FakeToolWindows([(dialog, 'Copying')])
		window = _FakeWidget(tool_windows)
		commands['ResumeToolWindow'](SimpleNamespace(_widget=window))()
		self.assertEqual([dialog], tool_windows.restored)
		self.assertEqual([], window.quicksearch_calls)

	def test_resume_command_uses_palette_to_choose_between_dialogs(self):
		commands = self._application_commands()
		first, second = object(), object()
		tool_windows = _FakeToolWindows([
			(first, 'Copying'), (second, 'Moving')
		])
		window = _FakeWidget(tool_windows, choice='Moving')
		commands['ResumeToolWindow'](SimpleNamespace(_widget=window))()
		self.assertEqual([second], tool_windows.restored)
		self.assertEqual(['Copying', 'Moving'], window.quicksearch_titles)

	def test_tool_window_commands_show_timed_empty_messages(self):
		commands = self._application_commands()
		window = _FakeWidget(_FakeToolWindows())
		command_window = SimpleNamespace(_widget=window)
		commands['ResumeToolWindow'](command_window)()
		commands['MinimizeToolWindow'](command_window)()
		self.assertEqual([
			('No minimized tool windows.', 3),
			('No tool window to minimize.', 3),
		], window.messages)

	def test_tray_commands_are_registered_only_when_tray_is_available(self):
		without_tray = self._application_commands()
		self.assertNotIn('MinimizeToTray', without_tray)
		self.assertNotIn('ToggleMinimizeToTray', without_tray)
		self.assertNotIn('ToggleStartWithWindows', without_tray)

		tray = MagicMock()
		with_tray = self._application_commands(tray)
		self.assertIn('MinimizeToTray', with_tray)
		self.assertIn('ToggleMinimizeToTray', with_tray)
		self.assertIn('ToggleStartWithWindows', with_tray)

		window = SimpleNamespace(_widget=MagicMock())
		with_tray['MinimizeToTray'](window)()
		tray.hide.assert_called_once_with()

		tray.toggle_minimize_to_tray.return_value = 'Minimize to tray is on.'
		with_tray['ToggleMinimizeToTray'](window)()
		window._widget.show_status_message.assert_called_once_with(
			'Minimize to tray is on.')

	@patch('fman.impl.plugins.builtin.toggle_start_with_windows')
	def test_start_with_windows_command_uses_tray_settings(self, toggle):
		tray = MagicMock()
		commands = self._application_commands(tray)
		window = SimpleNamespace(_widget=MagicMock())
		toggle.return_value = 'fman will start with Windows'

		commands['ToggleStartWithWindows'](window)()

		toggle.assert_called_once_with(tray.settings)
		window._widget.show_status_message.assert_called_once_with(
			'fman will start with Windows')

	def test_minimize_command_minimizes_the_latest_visible_dialog(self):
		commands = self._application_commands()
		dialog = _FakeMinimizableDialog()
		tool_windows = _FakeToolWindows(visible=dialog)
		commands['MinimizeToolWindow'](
			SimpleNamespace(_widget=_FakeWidget(tool_windows))
		)()
		self.assertEqual(1, dialog.minimize_count)

	def _application_commands(self, tray=None, window_chrome=None):
		registered = []
		args = [MagicMock() for _ in range(7)]
		with patch.object(
			BuiltinPlugin, '_register_application_command',
			side_effect=registered.append
		), patch.object(BuiltinPlugin, '_register_directory_pane_command'), \
			patch.object(BuiltinPlugin, '_register_file_system'), \
			patch.object(BuiltinPlugin, '_register_column'), \
			patch('fman.impl.plugins.builtin.is_mac', return_value=False):
			BuiltinPlugin(
				None, None, None, window_chrome or MagicMock(), MagicMock(),
				tray, *args)
		return {command.__name__: command for command in registered}


class _FakeToolWindows:
	def __init__(self, minimized=(), visible=None):
		self._minimized = list(minimized)
		self._visible = visible
		self.restored = []
	def minimized(self):
		return self._minimized
	def restore(self, dialog):
		self.restored.append(dialog)
	def visible_minimizable(self):
		return self._visible


class _FakeWidget:
	def __init__(self, tool_windows, choice=None):
		self._tool_windows = tool_windows
		self._choice = choice
		self.messages = []
		self.quicksearch_calls = []
		self.quicksearch_titles = []
	def get_tool_windows(self):
		return self._tool_windows
	def show_status_message(self, message, timeout):
		self.messages.append((message, timeout))
	def show_quicksearch(self, get_items):
		self.quicksearch_calls.append(get_items)
		items = get_items('')
		self.quicksearch_titles = [item.title for item in items]
		item = next((item for item in items if item.title == self._choice), None)
		return ('', item.value) if item is not None else None


class _FakeMinimizableDialog:
	def __init__(self):
		self.minimize_count = 0
	def minimize(self):
		self.minimize_count += 1
