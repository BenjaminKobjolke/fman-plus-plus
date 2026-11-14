import json
from threading import Event, Thread
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from fman.impl.metrics import (
	ApiBackend, AsynchronousMetrics, Metrics, NullBackend,
)


class MetricsTest(TestCase):
	def test_initialize_creates_and_persists_local_uuid(self):
		with TemporaryDirectory() as directory:
			path = directory + '/metrics.json'
			metrics = Metrics(path, NullBackend(), 'Windows', '1.2.3')

			with patch('fman.impl.metrics.uuid4', return_value='generated-id'):
				metrics.initialize()

			self.assertEqual('generated-id', metrics.get_user())
			with open(path) as file:
				self.assertEqual({'uuid': 'generated-id'}, json.load(file))

	def test_initialize_reuses_existing_uuid_and_enabled_flag(self):
		with TemporaryDirectory() as directory:
			path = directory + '/metrics.json'
			with open(path, 'w') as file:
				json.dump({'uuid': 'saved-id', 'enabled': False}, file)
			metrics = Metrics(path, NullBackend(), 'Windows', '1.2.3')

			metrics.initialize()

			self.assertEqual('saved-id', metrics.get_user())
			metrics.track('CommandCallback')

	def test_api_backend_waits_for_batch_size_and_posts_payload(self):
		backend = ApiBackend(
			'https://api.example.invalid/api/v1/metrics/events',
			'Windows', '1.2.3')
		with patch.object(backend, '_post') as post:
			for index in range(20):
				backend.track('install-id', 'CommandCallback', {'command': str(index)})

		post.assert_called_once()
		url, payload = post.call_args.args
		self.assertEqual('https://api.example.invalid/api/v1/metrics/events', url)
		self.assertEqual('install-id', payload['install_id'])
		self.assertEqual('Windows', payload['platform'])
		self.assertEqual('1.2.3', payload['app_version'])
		self.assertEqual(20, len(payload['events']))
		self.assertEqual({
			'event': 'CommandCallback',
			'properties': {'command': '0'},
		}, {key: payload['events'][0][key] for key in ('event', 'properties')})
		self.assertTrue(payload['events'][0]['occurred_at'].endswith('+00:00'))

	def test_flush_sends_remainder(self):
		backend = ApiBackend('https://api.example.invalid/events', 'Linux', '1.2.3')
		with patch.object(backend, '_post') as post:
			for _ in range(3):
				backend.track('install-id', 'StartedFman')
			backend.flush()

		post.assert_called_once()
		self.assertEqual(3, len(post.call_args.args[1]['events']))

	def test_requests_never_exceed_api_batch_limit(self):
		backend = ApiBackend(
			'https://api.example.invalid/events', 'Linux', '1.2.3',
			batch_size=101)
		with patch.object(backend, '_post') as post:
			for _ in range(101):
				backend.track('install-id', 'StartedFman')
			backend.flush()

		self.assertEqual([100, 1], [
			len(call.args[1]['events']) for call in post.call_args_list
		])

	def test_failed_post_is_logged_and_swallowed(self):
		backend = ApiBackend('https://api.example.invalid/events', 'Linux', '1.2.3')
		with (
			patch.object(backend, '_post', side_effect=OSError('offline')),
			patch('fman.impl.metrics.logger.exception') as log_exception,
		):
			for _ in range(20):
				backend.track('install-id', 'StartedFman')

		log_exception.assert_called_once()

	def test_non_scalar_properties_are_dropped(self):
		backend = ApiBackend('https://api.example.invalid/events', 'Linux', '1.2.3')
		with patch.object(backend, '_post') as post:
			backend.track('install-id', 'CommandCallback', {
				'valid': 4, 'also_valid': None, 'nested': {'private': 'value'},
				'items': ['a'],
			})
			backend.flush()

		properties = post.call_args.args[1]['events'][0]['properties']
		self.assertEqual({'valid': 4, 'also_valid': None}, properties)

	def test_null_backend_sends_nothing(self):
		backend = NullBackend()
		with patch('fman.impl.metrics.requests.post') as post:
			backend.track('install-id', 'StartedFman')
			backend.flush()

		post.assert_not_called()

	def test_async_flush_returns_when_metrics_were_not_initialized(self):
		metrics = MagicMock(spec=Metrics)
		asynchronous_metrics = AsynchronousMetrics(metrics)

		asynchronous_metrics.flush(timeout=1)

		metrics.flush.assert_not_called()

	def test_async_flush_waits_for_backend_flush(self):
		metrics = MagicMock(spec=Metrics)
		initialized = Event()
		flush_started = Event()
		finish_flush = Event()
		flush_returned = Event()
		metrics.flush.side_effect = lambda: (
			flush_started.set(), finish_flush.wait())
		asynchronous_metrics = AsynchronousMetrics(metrics)
		asynchronous_metrics.initialize(callback=initialized.set)
		self.assertTrue(initialized.wait(1))

		flusher = Thread(
			target=lambda: (
				asynchronous_metrics.flush(timeout=2), flush_returned.set()))
		flusher.start()
		self.assertTrue(flush_started.wait(1))
		self.assertFalse(flush_returned.wait(0.05))
		finish_flush.set()
		self.assertTrue(flush_returned.wait(1))
		flusher.join(1)
