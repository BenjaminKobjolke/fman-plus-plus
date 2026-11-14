from collections import deque
from datetime import datetime, timezone
from fbs_runtime.platform import is_linux
from logging import getLogger
from math import isfinite
from os import makedirs
from os.path import dirname
from queue import Queue
from threading import Event, Thread
from uuid import uuid4

import json
import requests


logger = getLogger(__name__)


def _get_data_for_tracking(install_id, event, properties=None):
	result = {'uuid': install_id, 'event': event}
	if properties:
		result.update(properties)
	return result


class MetricsError(Exception):
	pass


class Metrics:
	def __init__(self, json_path, backend, os, fman_version):
		self._json_path = json_path
		self._backend = backend
		self._user = None
		self._super_properties = {
			'os': os,
			'app_version': fman_version
		}
		self._enabled = True
	def initialize(self):
		try:
			json_dict = self._read_json()
		except ValueError:
			self._enabled = False
		except FileNotFoundError:
			self._user = str(uuid4())
			self._write_json({'uuid': self._user})
		except NotADirectoryError:
			# This happens when part of a path isn't a dir. Eg. install.txt/foo.
			# In this case, we will also not be able to save a generated UUID to
			# the file. So instead of generating a new UUID with every start, we
			# simply disable Metrics:
			self._enabled = False
		else:
			self._enabled = json_dict.get('enabled', True)
			try:
				self._user = json_dict['uuid']
			except KeyError:
				self._enabled = False
		if self._enabled and is_linux():
			# linux_distribution() is expensive. We perform it here (instead of,
			# say, the application context) because the present method is run
			# in a separate thread via AsynchronousMetrics.
			from distro import linux_distribution
			distribution, version = linux_distribution()[:2]
			if version:
				distribution += ' ' + version
			self._super_properties['distribution'] = distribution
	def get_user(self):
		return self._user
	def track(self, event, properties=None):
		if not self._enabled:
			return
		data = dict(self._super_properties)
		if properties:
			data.update(properties)
		try:
			self._backend.track(self._user, event, data)
		except MetricsError:
			pass
	def flush(self):
		self._backend.flush()
	def _read_json(self):
		with open(self._json_path, 'r') as f:
			return json.load(f)
	def _write_json(self, data):
		makedirs(dirname(self._json_path), exist_ok=True)
		with open(self._json_path, 'w') as f:
			json.dump(data, f)


class ApiBackend:
	DEFAULT_BATCH_SIZE = 20
	MAX_BATCH_SIZE = 100
	POST_TIMEOUT_SECONDS = 5

	def __init__(self, events_url, platform, app_version,
			batch_size=DEFAULT_BATCH_SIZE):
		self._events_url = events_url
		self._platform = platform
		self._app_version = app_version
		self._batch_size = min(max(1, batch_size), self.MAX_BATCH_SIZE)
		self._events = []
		self._install_id = None

	def track(self, install_id, event, properties=None):
		self._install_id = install_id
		self._events.append({
			'event': event,
			'occurred_at': datetime.now(timezone.utc).isoformat(),
			'properties': self._scalar_properties(properties),
		})
		if len(self._events) >= self._batch_size:
			self._send_batches(self._batch_size)

	def flush(self):
		self._send_batches(self.MAX_BATCH_SIZE)

	def get_data_for_tracking(self, install_id, event, properties=None):
		return _get_data_for_tracking(install_id, event, properties)

	@staticmethod
	def _scalar_properties(properties):
		if not properties:
			return {}
		return {
			key: value for key, value in properties.items()
			if value is None or isinstance(value, (str, int, float, bool))
			and (not isinstance(value, float) or isfinite(value))
		}

	def _send_batches(self, max_batch_size):
		while self._events:
			batch = self._events[:max_batch_size]
			del self._events[:len(batch)]
			payload = {
				'install_id': self._install_id,
				'platform': self._platform,
				'app_version': self._app_version,
				'events': batch,
			}
			try:
				self._post(self._events_url, payload)
			except Exception:
				logger.exception('Could not send usage metrics batch')

	@classmethod
	def _post(cls, url, payload):
		response = requests.post(url, json=payload, timeout=cls.POST_TIMEOUT_SECONDS)
		response.raise_for_status()


class NullBackend:
	def track(self, install_id, event, properties=None):
		pass
	def flush(self):
		pass
	def get_data_for_tracking(self, install_id, event, properties=None):
		return _get_data_for_tracking(install_id, event, properties)


class LoggingBackend:
	def __init__(self, backend, max_num_logs=1000):
		self._backend = backend
		self._logs = deque(maxlen=max_num_logs)
	def track(self, install_id, event, properties=None):
		data = self._backend.get_data_for_tracking(
			install_id, event, properties)
		self._logs.append(data)
		self._backend.track(install_id, event, properties)
	def flush(self):
		self._backend.flush()
	def write_logs(self, log_file_path):
		with open(log_file_path, 'w') as f:
			def fmt_log(data):
				return json.dumps(data, indent=4)
			f.write('\n\n'.join(map(fmt_log, self._logs)))


class AsynchronousMetrics:
	def __init__(self, metrics):
		self.past_events = []
		self._metrics = metrics
		self._queue = Queue()
		self._thread = Thread(target=self._work, daemon=True)
		self._running = False
	def initialize(self, callback=lambda: None):
		self._queue.put(self._metrics.initialize)
		self._queue.put(callback)
		self._running = True
		self._thread.start()
	def get_user(self):
		return self._metrics.get_user()
	def track(self, event, properties=None):
		self.past_events.append(event)
		self._queue.put(lambda: self._metrics.track(event, properties))
	def flush(self, timeout):
		if not self._running:
			return
		finished = Event()
		def flush_metrics():
			try:
				self._metrics.flush()
			finally:
				finished.set()
		self._queue.put(flush_metrics)
		finished.wait(timeout)
	def _work(self):
		while True:
			self._queue.get()()
			self._queue.task_done()
