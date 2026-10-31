from hashlib import md5
from PyQt5.QtCore import Qt
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

import json
import logging

_LOG = logging.getLogger(__name__)

# Blocking waits are bounded so a hung/foreign peer can never freeze startup.
_TIMEOUT_MS = 3000

def server_name_for(data_directory):
	# Per-user/per-install name so different OS users don't share one socket.
	digest = md5(data_directory.encode('utf-8')).hexdigest()[:12]
	return 'fman-si-' + digest

def open_paths_in_running_instance(
	main_window, plugin_support, session_manager, abs_paths
):
	# Handle a forwarded launch inside the already-running primary instance:
	# raise its window and open the paths, first one in the active pane.
	bring_to_front(main_window)
	if not abs_paths:
		return
	panes = panes_active_first(plugin_support, main_window)
	for path, pane in zip(abs_paths, panes):
		session_manager.open_path_in_pane(pane, path)
	if panes:
		panes[0].focus()

def bring_to_front(main_window):
	# showNormal() would also clear WindowMaximized, losing the saved window size.
	main_window.setWindowState(
		main_window.windowState() & ~Qt.WindowMinimized
	)
	main_window.show()
	main_window.raise_()
	main_window.activateWindow()

def panes_active_first(plugin_support, main_window):
	all_panes = plugin_support.get_panes()
	if not all_panes:
		return []
	# get_active_pane() reads live Qt focus, which no pane has while the window
	# is in the background (the usual case for a forwarded launch). Fall back to
	# the window's focusWidget(), which remembers the last-focused child across
	# deactivation, so the pane the user last used wins over a left-pane default.
	active = plugin_support.get_active_pane() \
			 or _pane_of_focus_widget(all_panes, main_window) \
			 or all_panes[0]
	return [active] + [pane for pane in all_panes if pane is not active]

def _pane_of_focus_widget(panes, main_window):
	focus_widget = main_window.focusWidget()
	if focus_widget is None:
		return None
	for pane in panes:
		widget = pane._widget
		if focus_widget is widget or widget.isAncestorOf(focus_widget):
			return pane
	return None

class SingleInstance:
	def __init__(self, server_name, on_paths_received):
		self._server_name = server_name
		self._on_paths_received = on_paths_received
		self._server = None
		self._client_socket = None
	def try_forward(self, abs_paths):
		# Return True if a running instance accepted the paths (caller exits),
		# False if no instance is listening (caller becomes the primary).
		socket = QLocalSocket()
		socket.connectToServer(self._server_name)
		if not socket.waitForConnected(_TIMEOUT_MS):
			return False
		socket.write(json.dumps(abs_paths).encode('utf-8'))
		socket.flush()
		socket.waitForBytesWritten(_TIMEOUT_MS)
		# waitForBytesWritten flushes to the OS, so the peer receives the
		# payload even once this process exits. Keep the socket referenced
		# rather than disconnecting: an early disconnect can drop the buffered
		# bytes before the peer reads them.
		self._client_socket = socket
		return True
	def start_listening(self):
		# removeServer clears a stale socket file left by a crash (no-op on
		# Windows named pipes).
		QLocalServer.removeServer(self._server_name)
		self._server = QLocalServer()
		if not self._server.listen(self._server_name):
			# Never crash startup over IPC: just run as a normal instance.
			_LOG.warning(
				'Could not listen on %s: %s',
				self._server_name, self._server.errorString()
			)
			self._server = None
			return
		self._server.newConnection.connect(self._on_new_connection)
	def _on_new_connection(self):
		socket = self._server.nextPendingConnection()
		if socket is None:
			return
		# The peer may have written and disconnected before we got here, in
		# which case the bytes are already buffered and waitForReadyRead would
		# report no *new* data. Only wait when nothing has arrived yet.
		# The payload is a short JSON path list, so a single read suffices.
		if socket.bytesAvailable() == 0:
			socket.waitForReadyRead(_TIMEOUT_MS)
		data = bytes(socket.readAll())
		socket.disconnectFromServer()
		try:
			paths = json.loads(data.decode('utf-8'))
		except (ValueError, UnicodeDecodeError):
			_LOG.warning('Received malformed single-instance message.')
			return
		if isinstance(paths, list):
			self._on_paths_received([str(p) for p in paths])
