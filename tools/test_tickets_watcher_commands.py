import re
import unittest
from pathlib import Path


TOOLS = Path(__file__).parent
COMMANDS = (
    "find_build_python.bat",
    "run_build_shutdown_tests.bat",
    "run_tests.bat",
    "unittest_with_timeout.bat",
    "update_windrop.bat",
)


class TicketsWatcherCommandsTest(unittest.TestCase):
    def test_scripts_do_not_wait_for_unsupported_prompts_or_windows(self):
        for name in COMMANDS:
            with self.subTest(name=name):
                script = (TOOLS / name).read_text(encoding="utf-8").lower()
                self.assertNotRegex(script, r"(?m)^\s*pause\s*(?:$|&)")
                self.assertNotRegex(script, r"(?m)^\s*start\s+(?!/wait\b)")

    def test_shutdown_tests_use_the_hang_timeout_wrapper(self):
        script = (TOOLS / "run_build_shutdown_tests.bat").read_text(encoding="utf-8")
        self.assertRegex(
            script,
            re.compile(
                r'call\s+"%~dp0unittest_with_timeout\.bat"\s+-v\s+'
                r'fman_unittest\.impl\.build_shutdown_test',
                re.IGNORECASE,
            ),
        )

    def test_unit_test_suites_print_each_test_result(self):
        script = (TOOLS / "run_tests.bat").read_text(encoding="utf-8")
        suite_calls = re.findall(
            r'call\s+"%~dp0unittest_with_timeout\.bat"\s+([^\r\n]+)',
            script,
            re.IGNORECASE,
        )

        self.assertEqual(len(suite_calls), 2, script)
        for arguments in suite_calls:
            with self.subTest(arguments=arguments):
                self.assertRegex(arguments, r"(?:^|\s)-v(?:\s|$)")

    def test_unit_test_runner_streams_suite_progress_to_stdout(self):
        script = (TOOLS / "run_tests.bat").read_text(encoding="utf-8")
        suite_labels = re.findall(
            r"(?im)^echo\s+(Running\s+unit\s+test\s+suite:[^\r\n]+)",
            script,
        )
        self.assertEqual(len(suite_labels), 2, script)

        suite_calls = re.findall(
            r'call\s+"%~dp0unittest_with_timeout\.bat"\s+([^\r\n]+)',
            script,
            re.IGNORECASE,
        )
        self.assertEqual(len(suite_calls), 2, script)
        for arguments in suite_calls:
            with self.subTest(arguments=arguments):
                self.assertRegex(arguments, r"2\s*>\s*&\s*1\s*$")


if __name__ == "__main__":
    unittest.main()
