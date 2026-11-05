"""Cached, background lookups for network host and share suggestions."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from threading import Lock, Thread
from time import monotonic

from fman import QuicksearchItem, translate
from fman.localization_keys import (
	GOTO_NETWORK_NO_ANSWER, GOTO_NETWORK_NO_SHARES, GOTO_NETWORK_SEARCHING,
)
from core.fs.local.windows.shares import list_connections, parse_share_address

CACHE_SECONDS = 300
FAILURE_RETRY_SECONDS = 30


def _list_servers() -> list[str]:
	from core.fs.local.windows.network import NetworkFileSystem
	return list(NetworkFileSystem().iterdir(''))


def _list_shares(server: str) -> list[str]:
	from core.fs.local.windows.network import NetworkFileSystem
	return list(NetworkFileSystem().iterdir(server))


def _network_errors() -> tuple[type[Exception], ...]:
	try:
		from win32wnet import error as WNetError
	except ImportError:
		return (OSError,)
	return OSError, WNetError


@dataclass(frozen=True)
class NetworkSuggestion:
	dirs: list[str]
	status: QuicksearchItem | None = None


class NetworkLookups:
	"""Share timestamped results between Go To dialogs without blocking them."""

	def __init__(
			self, list_servers: Callable[[], list[str]] = _list_servers,
			list_shares: Callable[[str], list[str]] = _list_shares,
			clock: Callable[[], float] = monotonic,
			start_thread: Callable[[Callable[[], None]], None] | None = None
	) -> None:
		self._list_servers = list_servers
		self._list_shares = list_shares
		self._clock = clock
		self._start_thread = start_thread or self._start_default_thread
		self._lock = Lock()
		self._hosts = None
		self._shares = {}
		self._running = set()
		self._callbacks = {}
	def hosts(self, on_done: Callable[[], None]) -> tuple[list[str] | None, bool]:
		return self._get('hosts', None, on_done)
	def shares(
			self, server: str, on_done: Callable[[], None]
	) -> tuple[list[str] | None, bool]:
		return self._get(
			'shares', server.lower(), on_done,
			lambda: self._list_shares(server),
		)
	def _get(self, kind, key, on_done, lookup=None):
		cache_key = (kind, key)
		with self._lock:
			cache = self._hosts if kind == 'hosts' else self._shares.get(key)
			cache_ttl = (
				CACHE_SECONDS if cache and cache[1] is not None
				else FAILURE_RETRY_SECONDS
			)
			if cache and self._clock() - cache[0] < cache_ttl:
				return cache[1], False
			if cache_key in self._running:
				if on_done not in self._callbacks[cache_key]:
					self._callbacks[cache_key].append(on_done)
				return None, True
			self._running.add(cache_key)
			self._callbacks[cache_key] = [on_done]
			if lookup is None:
				lookup = self._list_servers

		def worker():
			try:
				result = list(lookup())
			except _network_errors():
				result = None
			with self._lock:
				entry = (self._clock(), result)
				if kind == 'hosts':
					self._hosts = entry
				else:
					self._shares[key] = entry
				self._running.remove(cache_key)
				callbacks = self._callbacks.pop(cache_key)
			for callback in callbacks:
				callback()
		try:
			self._start_thread(worker)
		except Exception:
			with self._lock:
				self._running.discard(cache_key)
				self._callbacks.pop(cache_key, None)
			raise
		return None, True
	@staticmethod
	def _start_default_thread(target: Callable[[], None]) -> None:
		Thread(target=target, daemon=True).start()


_LOOKUPS = None


def _get_lookups() -> NetworkLookups:
	global _LOOKUPS
	if _LOOKUPS is None:
		_LOOKUPS = NetworkLookups()
	return _LOOKUPS


class NetworkSuggestions:
	"""Suggest visited and discovered hosts/shares for UNC queries."""

	def __init__(
			self, visited_paths: Iterable[str],
			lookups: NetworkLookups | None = None,
			list_connections_: Callable[[], list] | None = None
	) -> None:
		self._lookups = lookups or _get_lookups()
		self._refresh = None
		self._hosts = {}
		self._shares = {}
		try:
			connections = (list_connections_ or list_connections)()
		except _network_errors():
			connections = []
		for path in list(visited_paths) + [
			connection.remote_name for connection in connections
		]:
			if not path.startswith(('\\\\', '//')):
				continue
			address = parse_share_address(path)
			if address is None:
				continue
			host_key = address.server.lower()
			self._hosts.setdefault(host_key, address.server)
			if address.share:
				share_path = (
					'\\\\' + self._hosts[host_key] + '\\' + address.share
				)
				self._shares.setdefault(host_key, {})[
					address.share.lower()
				] = share_path

	def set_refresh(self, fn: Callable[[], None]) -> None:
		self._refresh = fn
	def __call__(self, query: str) -> NetworkSuggestion | None:
		if query in ('\\\\', '//'):
			return self._hosts_for(query)
		if not query.startswith(('\\\\', '//')):
			return None
		address = parse_share_address(query)
		if address is None or address.subpath:
			return None
		if any(char in query[2 + len(address.server):] for char in '\\\\/'):
			return self._shares_for(address.server, query)
		return self._hosts_for(query)
	def _hosts_for(self, query):
		result, pending = self._lookups.hosts(self._on_done)
		hosts = dict(self._hosts)
		if result is not None:
			for host in result:
				hosts.setdefault(host.lower(), host)
		dirs = ['\\\\' + host for host in hosts.values()]
		status = self._status(query, GOTO_NETWORK_SEARCHING) if pending else None
		return NetworkSuggestion(dirs, status)
	def _shares_for(self, server, query):
		result, pending = self._lookups.shares(server, self._on_done)
		shares = dict(self._shares.get(server.lower(), {}))
		if result is not None:
			for share in result:
				path = '\\\\' + server + '\\' + share
				shares.setdefault(share.lower(), path)
		dirs = list(shares.values())
		if pending:
			key = GOTO_NETWORK_SEARCHING
		elif result is None:
			key = GOTO_NETWORK_NO_ANSWER
		elif not result and not shares:
			key = GOTO_NETWORK_NO_SHARES
		else:
			key = None
		return NetworkSuggestion(dirs, self._status('\\\\' + server, key))
	def _status(self, prefix: str, key: str | None) -> QuicksearchItem | None:
		if key is None:
			return None
		return QuicksearchItem(None, prefix, hint=translate(key))
	def _on_done(self):
		if self._refresh is not None:
			self._refresh()
