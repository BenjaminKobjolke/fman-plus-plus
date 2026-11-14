from fman.impl.app_error_report import AppErrorReporter
from unittest import TestCase
from unittest.mock import MagicMock, patch


class AppErrorReporterTest(TestCase):
	def setUp(self):
		self.settings = MagicMock()
		self.settings.get.return_value = True
		self.reporter = AppErrorReporter(
			'https://example.invalid', '1.2.3', self.settings)

	def test_create_report_redacts_secrets_and_caps_text(self):
		error = RuntimeError(
			'email jane@example.com token=abcdefghijklmnop '
			'password: hunter2 key=private-value '
			'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signaturevalue123456 '
			'ghp_abcdefghijklmnopqrstuvwxyz1234567890')
		report = self.reporter.create_report(
			error, stack='Bearer abcdefghijklmnopqrstuvwxyz0123456789')

		self.assertEqual('unhandled', report['kind'])
		self.assertIn(report['platform'], ('windows', 'mac', 'linux'))
		self.assertEqual('1.2.3', report['app_version'])
		self.assertEqual('RuntimeError', report['exception_type'])
		self.assertNotIn('jane@example.com', report['message'])
		self.assertNotIn('abcdefghijklmnop', report['message'])
		self.assertNotIn('hunter2', report['message'])
		self.assertNotIn('private-value', report['message'])
		self.assertNotIn('eyJhbGciOiJIUzI1NiJ9', report['message'])
		self.assertNotIn('ghp_abcdefghijklmnopqrstuvwxyz1234567890', report['message'])
		self.assertNotIn('abcdefghijklmnopqrstuvwxyz0123456789', report['stack'])
		self.assertEqual('<redacted>', report['message'].split('token=')[1].split()[0])
		self.assertEqual('Bearer <redacted>', report['stack'])

		report = self.reporter.create_report(
			RuntimeError('m' * 2500), stack='s' * 33000)
		self.assertEqual(2000, len(report['message']))
		self.assertEqual(32000, len(report['stack']))

	def test_create_report_has_optional_plugin_and_os_fields(self):
		with (
			patch('fman.impl.app_error_report.platform.system', return_value='Linux'),
			patch('fman.impl.app_error_report.platform.release', return_value='6.1'),
		):
			report = self.reporter.create_report(
				ValueError('broken'), kind='plugin', plugin='MyPlugin', stack='trace')
		self.assertEqual({
			'kind': 'plugin', 'platform': 'linux', 'app_version': '1.2.3',
			'exception_type': 'ValueError', 'message': 'broken', 'stack': 'trace',
			'os_version': '6.1', 'plugin': 'MyPlugin',
		}, report)

	def test_reporting_requires_explicit_consent(self):
		self.settings.get.return_value = False
		self.assertFalse(self.reporter.is_enabled)
		self.assertFalse(self.reporter.report(RuntimeError('broken')))
		self.assertFalse(self.reporter.is_enabled)

	def test_report_deduplicates_and_stops_after_ten_reports(self):
		with patch('fman.impl.app_error_report.Thread.start') as start:
			self.assertTrue(self.reporter.report(RuntimeError('same')))
			self.assertFalse(self.reporter.report(RuntimeError('same')))
			for index in range(9):
				self.assertTrue(self.reporter.report(RuntimeError(str(index))))
			self.assertFalse(self.reporter.report(RuntimeError('eleventh')))

		self.assertEqual(10, start.call_count)

	def test_failed_post_is_logged_and_swallowed_in_daemon_thread(self):
		report = self.reporter.create_report(RuntimeError('broken'), stack='trace')
		with (
			patch('fman.impl.app_error_report.Thread') as thread,
			patch(
				'fman.impl.app_error_report.requests.post',
				side_effect=OSError('offline')
			),
			patch('fman.impl.app_error_report.logger.exception') as log_exception,
		):
			self.assertTrue(self.reporter.send(report))
			thread.assert_called_once_with(
				target=thread.call_args.kwargs['target'], daemon=True)
			thread.call_args.kwargs['target']()

		log_exception.assert_called_once()
