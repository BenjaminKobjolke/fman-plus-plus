import os
from pathlib import Path
import sys
import tempfile
from unittest import main
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import test_fman_ui_session_reaper
import test_fman_ui_fixtures
import test_fman_ui_network_share
import test_fman_ui_launch
import test_fman_ui_startup_prompts
import test_fman_ui_restart
import test_fman_ui_build_info
import test_fman_ui_guards
import test_fman_ui_window_size
import test_fman_ui_process_launch
import test_fman_ui_recycle_cleanup
import test_fman_ui_driver
from parser import parser
import fman_ui


class FmanUiRootTest(TestCase):
	def test_uses_system_temp_directory_when_temp_is_unset(self):
		with patch.dict(os.environ), \
			patch.object(tempfile, 'gettempdir', return_value='system-temp'):
			os.environ.pop('TEMP', None)
			self.assertEqual(Path('system-temp') / 'fman-ui', fman_ui._root())


class FmanUiParserTest(TestCase):
	def test_accepts_hover_and_window(self):
		hover = parser().parse_args(['hover', '--x', '1', '--y', '2'])
		window = parser().parse_args([
			'window', '--width', '800', '--height', '600'])
		self.assertEqual(('hover', 1, 2, 500), (
			hover.action, hover.x, hover.y, hover.settle))
		self.assertEqual(('window', 800, 600), (
			window.action, window.width, window.height))

	def test_accepts_large_and_core_settings(self):
		args = parser().parse_args([
			'launch', '--large', '5000', '--core-settings', '{}'])
		self.assertEqual(5000, args.large)
		self.assertEqual('{}', args.core_settings)

	def test_accepts_deep(self):
		args = parser().parse_args(['launch', '--deep', '10'])
		self.assertEqual(10, args.deep)

	def test_accepts_network_share(self):
		self.assertTrue(parser().parse_args(
			['launch', '--network-share']).network_share)
		self.assertFalse(parser().parse_args(['launch']).network_share)

	def test_accepts_previous_version(self):
		args = parser().parse_args([
			'launch', '--previous-version', '1.0.0'])
		self.assertEqual('1.0.0', args.previous_version)

	def test_accepts_first_start(self):
		args = parser().parse_args(['launch', '--first-start'])
		self.assertTrue(args.first_start)

	def test_accepts_demo_id(self):
		args = parser().parse_args(['launch', '--demo', '1'])
		self.assertEqual(1, args.demo)



def load_tests(loader, tests, pattern):
	tests.addTests(loader.loadTestsFromTestCase(FmanUiRootTest))
	tests.addTests(loader.loadTestsFromTestCase(FmanUiParserTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_driver.FmanUiTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_recycle_cleanup.RecycleCleanupTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_session_reaper.SessionReaperTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_fixtures.FixturesTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_network_share.NetworkShareTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_launch.FmanUiLaunchTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_startup_prompts.StartupPromptsTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_restart.FmanUiRestartTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_build_info.BuildInfoTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_guards.GuardsTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_process_launch.ProcessLaunchTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_window_size.WindowSizeTest))
	return tests


if __name__ == '__main__':
	main()
