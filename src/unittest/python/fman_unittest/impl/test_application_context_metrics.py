from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from fman.impl.application_context import (
	DevelopmentApplicationContext, FrozenApplicationContext,
)
from fman.impl.metrics import ApiBackend, LoggingBackend, NullBackend


class ApplicationContextMetricsTest(TestCase):
	def _context(self, context_type=DevelopmentApplicationContext):
		return object.__new__(context_type)

	def test_start_metrics_requires_explicit_usage_consent(self):
		settings = MagicMock()
		settings.get.return_value = True
		metrics = MagicMock()
		context = SimpleNamespace(
			local_settings=settings, metrics=metrics,
			_on_metrics_initialised=lambda: None)

		DevelopmentApplicationContext._start_metrics(context)

		settings.get.assert_called_once_with('usage_metrics')
		metrics.initialize.assert_called_once_with(
			callback=context._on_metrics_initialised)
		metrics.track.assert_called_once_with('StartedFman')

	def test_start_metrics_stays_off_without_true_consent(self):
		settings = MagicMock()
		settings.get.return_value = None
		metrics = MagicMock()
		context = SimpleNamespace(
			local_settings=settings, metrics=metrics,
			_on_metrics_initialised=lambda: None)

		DevelopmentApplicationContext._start_metrics(context)

		metrics.initialize.assert_not_called()
		metrics.track.assert_not_called()

	def test_development_uses_null_backend(self):
		context = self._context()
		context.__dict__['metrics_logging_enabled'] = False

		self.assertIsInstance(context.metrics_backend, NullBackend)

	def test_frozen_uses_api_backend_and_optional_logging_wrapper(self):
		context = self._context(FrozenApplicationContext)
		with patch.object(
			FrozenApplicationContext, 'metrics_logging_enabled', True
		):
			backend = context.metrics_backend

		self.assertIsInstance(backend, LoggingBackend)
		self.assertIsInstance(backend._backend, ApiBackend)
		self.assertTrue(backend._backend._events_url.endswith(
			'/api/v1/metrics/events'))

	def test_quit_waits_for_metrics_flush_before_writing_logs(self):
		order = []
		metrics = MagicMock()
		metrics.flush.side_effect = lambda timeout: order.append(
			('flush', timeout))
		backend = MagicMock()
		backend.write_logs.side_effect = lambda path: order.append(
			('write_logs', path))
		context = SimpleNamespace(
			scripting_control=MagicMock(), config=MagicMock(), metrics=metrics,
			metrics_logging_enabled=True, metrics_backend=backend,
			_get_metrics_json_path=lambda: 'C:/data/Metrics.json')
		with patch.object(
			DevelopmentApplicationContext, '_get_metrics_json_path',
			return_value='C:/data/Metrics.json'
		):
			DevelopmentApplicationContext.on_quit(context)

		self.assertEqual('flush', order[0][0])
		self.assertEqual(3, order[0][1])
		self.assertEqual('write_logs', order[1][0])
