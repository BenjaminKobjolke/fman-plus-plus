"""Build and deliver privacy-filtered reports for application errors."""

import hashlib
import json
import logging
import platform
import re
import traceback
from threading import Lock, Thread

import requests


ERROR_REPORTS_SETTING = 'error_reports'
MAX_MESSAGE_LENGTH = 2000
MAX_STACK_LENGTH = 32000
MAX_REPORTS_PER_START = 10
POST_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)

_EMAIL = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.IGNORECASE)
_JWT = re.compile(
	r'\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b')
_BEARER = re.compile(r'\bBearer\s+\S+', re.IGNORECASE)
_SECRET_VALUE = re.compile(
	r'(?i)(\b(?:password|passphrase|token|secret|key|api[_-]?key|access[_-]?key|'
	r'private[_-]?key)\b\s*[:=]\s*)(["\']?)([^\s,;&}\]\'" ]+)')
_LONG_TOKEN = re.compile(
	r'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|'
	r'sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|'
	r'ya29\.[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,})\b', re.IGNORECASE)


def _redact(text):
	text = _SECRET_VALUE.sub(r'\1<redacted>', text)
	text = _BEARER.sub('Bearer <redacted>', text)
	text = _JWT.sub('<redacted>', text)
	text = _EMAIL.sub('<redacted>', text)
	return _LONG_TOKEN.sub('<redacted>', text)


class AppErrorReporter:
	"""Redact, limit and asynchronously send error reports to fman-api."""

	def __init__(self, api_url, app_version, settings):
		self._endpoint = api_url.rstrip('/') + '/api/v1/app-errors'
		self._app_version = app_version
		self._settings = settings
		self._lock = Lock()
		self._reported = set()

	@property
	def is_enabled(self):
		return self._settings.get(ERROR_REPORTS_SETTING, False) is True

	def create_report(self, exception, kind='unhandled', plugin=None, stack=None):
		if stack is None:
			stack = ''.join(traceback.format_exception(
				type(exception), exception, exception.__traceback__))
		current_platform = platform.system().lower()
		if current_platform == 'darwin':
			current_platform = 'mac'
		elif current_platform.startswith('win'):
			current_platform = 'windows'
		elif current_platform.startswith('linux'):
			current_platform = 'linux'
		os_version = platform.release()
		report = {
			'kind': kind,
			'platform': current_platform,
			'app_version': self._app_version,
			'exception_type': type(exception).__name__,
			'message': _redact(str(exception))[:MAX_MESSAGE_LENGTH],
			'stack': _redact(stack)[:MAX_STACK_LENGTH],
		}
		if os_version:
			report['os_version'] = os_version
		if plugin is not None:
			report['plugin'] = plugin
		return report

	def report(self, exception, kind='unhandled', plugin=None):
		if not self.is_enabled:
			return False
		return self.send(self.create_report(exception, kind, plugin))

	def send(self, report):
		"""Queue one report; return false for duplicates or the per-start limit."""
		report = dict(report)
		key = hashlib.sha256(json.dumps(
			report, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
		with self._lock:
			if key in self._reported or len(self._reported) >= MAX_REPORTS_PER_START:
				return False
			self._reported.add(key)
		try:
			Thread(target=lambda: self._post(report), daemon=True).start()
		except Exception:
			logger.exception('Could not start app error report transport')
		return True

	def _post(self, report):
		try:
			response = requests.post(
				self._endpoint, json=report, timeout=POST_TIMEOUT_SECONDS)
			response.raise_for_status()
		except Exception:
			# The transport must never feed a delivery failure back to sys.excepthook.
			logger.exception('App error report delivery failed')
