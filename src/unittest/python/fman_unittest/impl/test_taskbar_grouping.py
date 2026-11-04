import sys
import unittest
from unittest.mock import patch

if sys.platform != 'win32':
	raise unittest.SkipTest('Taskbar grouping is only available on Windows')

from fman.impl import taskbar_grouping


class TaskbarGroupingTest(unittest.TestCase):
	def test_default_and_enabled_setting_keep_windows_grouped(self):
		with patch.object(taskbar_grouping, '_set_app_id') as set_app_id:
			taskbar_grouping.apply({})
			taskbar_grouping.apply({'taskbar_grouping': True})
		set_app_id.assert_not_called()

	def test_disabled_setting_assigns_process_specific_app_id(self):
		with patch.object(taskbar_grouping.os, 'getpid', return_value=123), \
				patch.object(taskbar_grouping, '_set_app_id') as set_app_id:
			taskbar_grouping.apply({'taskbar_grouping': False})
		set_app_id.assert_called_once_with('fman++.123')

	def test_setter_failure_is_logged_and_does_not_escape(self):
		with patch.object(
			taskbar_grouping, '_set_app_id', side_effect=OSError('unavailable')
		), self.assertLogs(taskbar_grouping.__name__, level='WARNING'):
			taskbar_grouping.apply({'taskbar_grouping': False})

	def test_nonzero_hresult_is_logged(self):
		with patch.object(taskbar_grouping, '_set_app_id', return_value=1), \
				self.assertLogs(taskbar_grouping.__name__, level='WARNING'):
			taskbar_grouping.apply({'taskbar_grouping': False})


if __name__ == '__main__':
	unittest.main()
