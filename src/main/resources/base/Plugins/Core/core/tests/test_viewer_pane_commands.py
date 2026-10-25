"""Viewer access to opted-in pane commands."""
from core.tests.viewer_stubs import StubPane
from fman import DirectoryPaneCommand
from fman.impl.plugins.command_registry import PaneCommandRegistry
from fman.impl.util.qt.key_event import QtKeyEvent
from PyQt5.QtCore import Qt
from unittest import TestCase
from unittest.mock import patch


class ViewerCommandFlagTest(TestCase):
	def test_registry_uses_inherited_flag_and_registration(self):
		class Plain(DirectoryPaneCommand):
			pass
		class Enabled(DirectoryPaneCommand):
			usable_in_viewer = True
		class Inherited(Enabled):
			pass
		class Disabled(Enabled):
			usable_in_viewer = False
		registry = PaneCommandRegistry(None, None)
		for cls in (Plain, Enabled, Inherited, Disabled):
			registry.register_command(cls.__name__, cls)
		self.assertEqual({'Enabled', 'Inherited'}, registry.get_viewer_commands())
		registry.unregister_command('Enabled')
		self.assertEqual({'Inherited'}, registry.get_viewer_commands())

	def test_core_flags_only_suitable_commands(self):
		import core
		expected = {
			'AddPane', 'Copy', 'Move', 'RemovePane', 'Symlink', 'CopyPathsToClipboard',
			'CopyFileName', 'CopyFilePath',
			'OpenWithEditor', 'OpenTerminal', 'OpenNativeFileManager',
			'ShowExplorerProperties', 'Pack', 'OpenWith',
			'ShowOnlyActivePane', 'ShowAllPanes', 'SetTextEditor',
		}
		actual = {
			name for name in dir(core)
			if isinstance(getattr(core, name), type)
			and issubclass(getattr(core, name), DirectoryPaneCommand)
			and getattr(core, name).usable_in_viewer
		}
		self.assertEqual(expected, actual)


class PaneCommandLookupTest(TestCase):
	def test_global_bindings_and_shadowing(self):
		from core.viewer_pane_commands import pane_command_for
		pane = StubPane([], viewer_commands={'copy', 'move'})
		bindings = [
			{'keys': ['F5'], 'command': 'copy'},
			{'keys': ['F6'], 'command': 'move'},
			{'keys': ['Down'], 'command': 'move_cursor_down'},
		]
		with patch('core.viewer_pane_commands.load_json', return_value=bindings):
			self.assertEqual(
				'copy', pane_command_for(pane, QtKeyEvent(Qt.Key_F5, Qt.NoModifier))
			)
			self.assertEqual(
				'move', pane_command_for(pane, QtKeyEvent(Qt.Key_F6, Qt.NoModifier))
			)
			self.assertIsNone(pane_command_for(
				pane, QtKeyEvent(Qt.Key_Down, Qt.NoModifier)
			))
			bindings.insert(0, {'keys': ['F5'], 'command': 'do_nothing'})
			bindings.insert(0, {'keys': [], 'command': 'copy'})
			self.assertIsNone(pane_command_for(
				pane, QtKeyEvent(Qt.Key_F5, Qt.NoModifier)
			))


class PaneCommandRunTest(TestCase):
	def test_parks_and_restores_selection_even_on_error(self):
		from core.viewer_pane_commands import run_pane_command
		def fail(_name):
			raise ValueError()
		pane = StubPane(['file:///a.png'], on_run=fail)
		pane.selected = ['file:///a.png', 'file:///b.png']
		with patch('core.viewer_pane_commands._in_background', lambda work: work()), \
				patch('core.viewer_pane_commands.exists', return_value=True):
			with self.assertRaises(ValueError):
				run_pane_command(pane, 'copy', 'image', lambda: None)
		self.assertEqual([[]], pane.selection_during_command)
		self.assertEqual(['file:///a.png', 'file:///b.png'], pane.selected)

	def test_parks_and_restores_selection_on_success(self):
		from core.viewer_pane_commands import run_pane_command
		pane = StubPane(['file:///a.png'])
		pane.selected = ['file:///a.png', 'file:///b.png']
		with patch('core.viewer_pane_commands._in_background', lambda work: work()), \
				patch('core.viewer_pane_commands.exists', return_value=True):
			run_pane_command(pane, 'copy', 'image', lambda: None)
		self.assertEqual([[]], pane.selection_during_command)
		self.assertEqual(['file:///a.png', 'file:///b.png'], pane.selected)

	def test_runs_later_and_checks_if_file_disappeared(self):
		from core.viewer_pane_commands import run_pane_command
		urls = ['file:///a.png', 'file:///b.png']
		pane = StubPane(urls, on_run=lambda _name: urls.remove('file:///a.png'))
		work = []
		with patch('core.viewer_pane_commands._in_background', work.append), \
				patch('core.viewer_pane_commands.exists', lambda url: url in urls), \
				patch('core.viewer_pane_commands.after_file_gone') as gone:
			run_pane_command(pane, 'move', 'image', lambda: None)
			self.assertEqual([], pane.commands)
			work[0]()
			gone.assert_called_once()
		self.assertEqual(['move'], pane.commands)

	def test_copy_leaves_viewer_alone(self):
		from core.viewer_pane_commands import run_pane_command
		pane = StubPane(['file:///a.png'])
		with patch('core.viewer_pane_commands._in_background', lambda work: work()), \
				patch('core.viewer_pane_commands.exists', return_value=True), \
				patch('core.viewer_pane_commands.after_file_gone') as gone:
			run_pane_command(pane, 'copy', 'image', lambda: None)
			gone.assert_not_called()
		self.assertEqual(['copy'], pane.commands)
		self.assertEqual([[]], pane.selection_during_command)

	def test_empty_selection_needs_no_selection_changes(self):
		from core.viewer_pane_commands import run_pane_command
		pane = StubPane(['file:///a.png'])
		with patch('core.viewer_pane_commands._in_background', lambda work: work()), \
				patch('core.viewer_pane_commands.exists', return_value=True), \
				patch.object(pane, 'clear_selection') as clear, \
				patch.object(pane, 'select') as select:
			run_pane_command(pane, 'copy', 'image', lambda: None)
			clear.assert_not_called()
			select.assert_not_called()


class PaneCommandActionsTest(TestCase):
	def test_rows_use_global_bindings_and_bound_actions(self):
		from core.key_bindings import KEY_BINDINGS_FILE
		from core.viewer_pane_commands import pane_command_actions
		pane = StubPane([], aliases={'move': 'Move', 'copy': 'Copy'},
			viewer_commands={'move', 'copy', 'hidden'})
		bindings = [{'keys': ['F5'], 'command': 'copy'}]
		run = []
		with patch('core.viewer_pane_commands.load_json', return_value=bindings):
			rows = pane_command_actions(pane, run.append)
		self.assertEqual(['Copy', 'Move'], [row[0] for row in rows])
		self.assertEqual('F5', rows[0][2])
		self.assertEqual(('copy', KEY_BINDINGS_FILE), rows[0][3:])
		for row in rows:
			row[1]()
		self.assertEqual(['copy', 'move'], run)
