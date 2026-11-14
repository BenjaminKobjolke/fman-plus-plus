from pathlib import Path
import sys
from unittest import main

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import test_fman_ui_session_reaper
import test_fman_ui_fixtures
import test_fman_ui_launch
import test_fman_ui_restart
import test_fman_ui_build_info
import test_fman_ui_guards
import test_fman_ui_process_launch
import test_fman_ui_recycle_cleanup
import test_fman_ui_driver



def load_tests(loader, tests, pattern):
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_driver.FmanUiTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_recycle_cleanup.RecycleCleanupTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_session_reaper.SessionReaperTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_fixtures.FixturesTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_launch.FmanUiLaunchTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_restart.FmanUiRestartTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_build_info.BuildInfoTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_guards.GuardsTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_process_launch.ProcessLaunchTest))
	return tests


if __name__ == '__main__':
	main()
