"""
A minimal read-only video viewer shown inside a directory pane, in place of
the file list - the "View file" command's video counterpart to
core/imageviewer.py's PaneImageView (see ViewFile in core/commands/opening.py,
which routes to whichever viewer matches the file's extension via
is_video()). Reuses core/textviewer_pane.py's pane-mounting glue
(begin_new_view/mount_view/close_view) as-is, the same way the image viewer
does - no shared-code changes needed.

Playback is backed by python-mpv (libmpv) rather than QtMultimedia so
mp4/mkv/webm/avi/mov play identically on Windows/macOS/Linux without relying
on OS-provided codecs.

`mpv` is imported lazily (inside show_video_viewer), not at module level:
importing it raises OSError immediately if the native libmpv binary isn't on
the system - and since this module is imported unconditionally by
core/commands/opening.py, an eager import would crash the whole Core plugin
(every command, not just video viewing) on a machine without libmpv
installed. Deferring it means is_video()/browsing files still work, and only
actually opening a video needs the native library.

show_video_viewer() itself is deliberately NOT @run_in_main_thread: fman
already runs each DirectoryPaneCommand's __call__ (and so ViewFile, its
caller) on its own background thread, and ensure_libmpv_on_path() needs that
thread to show its progress dialog without freezing the Qt event loop for
the download's multi-second duration (see core/libmpv.py). Only the actual
Qt widget construction (_open_video_view) marshals onto the main thread.
"""
from core.key_bindings import dispatch_bindable_command, VIEWER_KEY_BINDINGS_FILE
from core.libmpv import ensure_libmpv_on_path
from core.settings import get_setting, save_setting, SETTINGS_FILE
from core.textviewer_pane import begin_new_view, mount_view, \
	close_view as close_text_viewer
from core.viewer_navigation import open_viewer_palette, ViewerNavigator
from core.viewer_status import viewer_status
from fman import show_alert, load_json
from fman.impl.util.qt.key_event import QtKeyEvent
from fman.impl.util.qt.thread import run_in_main_thread
from fman.url import as_human_readable
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

import sys

VIDEO_EXTENSIONS = (
	'.mp4', '.m4v', '.mkv', '.webm', '.avi', '.mov', '.wmv', '.flv',
	'.mpg', '.mpeg', '.ogv', '.3gp', '.ts',
)

_VOLUME_KEY = 'video_viewer_volume'
_MUTE_KEY = 'video_viewer_muted'

def is_video(url):
	return url.lower().endswith(VIDEO_EXTENSIONS)

def get_saved_volume():
	return get_setting(SETTINGS_FILE, _VOLUME_KEY)

def save_volume(volume):
	save_setting(SETTINGS_FILE, _VOLUME_KEY, volume)

def get_saved_mute():
	return bool(get_setting(SETTINGS_FILE, _MUTE_KEY, False))

def save_mute(muted):
	save_setting(SETTINGS_FILE, _MUTE_KEY, bool(muted))

def format_time(seconds):
	if seconds is None or seconds < 0:
		seconds = 0
	seconds = int(seconds)
	hours, remainder = divmod(seconds, 3600)
	minutes, secs = divmod(remainder, 60)
	if hours:
		return '%d:%02d:%02d' % (hours, minutes, secs)
	return '%d:%02d' % (minutes, secs)

class PaneVideoView(QWidget):
	def __init__(self, on_close, on_switch, pane, bg):
		super().__init__()
		self._on_close = on_close
		self._on_switch = on_switch
		# No on_renamed: nothing here is addressed by path once playback has
		# started, and navigation follows the pane's cursor, which _Rename
		# moves to the new name.
		self._nav = ViewerNavigator(pane, 'video', on_close)
		self._player = None
		self._muted = False
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)
		# Native child surface mpv renders into directly - required so libmpv
		# can embed via its own window handle (wid) instead of Qt painting.
		self._surface = QWidget()
		self._surface.setAttribute(Qt.WA_DontCreateNativeAncestors)
		self._surface.setAttribute(Qt.WA_NativeWindow)
		self._surface.setStyleSheet('background-color: %s;' % bg)
		layout.addWidget(self._surface, stretch=1)
		self._time_label = QLabel('0:00 / 0:00')
		self._time_label.setAlignment(Qt.AlignCenter)
		self._time_label.setStyleSheet('QLabel { background-color: %s; }' % bg)
		layout.addWidget(self._time_label)
		self._timer = QTimer(self)
		self._timer.timeout.connect(self._update_time_label)

	def start_playback(self, mpv_module, path):
		# Must run after this view is mounted into the pane's layout and
		# shown (see show_video_viewer) - grabbing winId() and starting
		# playback beforehand embeds mpv into a surface that has no real
		# size/visibility yet, which renders as a permanently grey box even
		# though audio (which doesn't need the visual embed) plays fine.
		self._player = mpv_module.MPV(
			wid=str(int(self._surface.winId())),
			input_default_bindings=False,
			input_vo_keyboard=False,
			osc=False,
			# Default keep-open=no unloads the file at EOF - time_pos/
			# duration go None (readout falls to 0:00/0:00) and there's
			# no loaded file left for Space/seek to act on. keep-open=
			# yes pauses on the last frame instead, keeping playback
			# state alive.
			keep_open='yes',
		)
		self._player.play(path)
		# Restore last-used volume/mute (see save_volume/save_mute below) -
		# None means nothing saved yet, so leave mpv's own default (100).
		saved_volume = get_saved_volume()
		if saved_volume is not None:
			self._player.volume = saved_volume
		self._muted = get_saved_mute()
		self._player.mute = self._muted
		# Capture as a local, not self, so the lambda doesn't keep this view
		# alive via a reference cycle through its own destroyed signal.
		player = self._player
		self.destroyed.connect(lambda: player.terminate())
		self._timer.start(250)

	def keyPressEvent(self, event):
		if (event.key() == Qt.Key_P and event.modifiers() & Qt.ControlModifier
				and event.modifiers() & Qt.ShiftModifier):
			# Own palette, not fman's global Ctrl+Shift+P - see
			# PaneTextView.keyPressEvent for why.
			self._open_palette()
			return
		key_event = QtKeyEvent(event.key(), event.modifiers())
		key_bindings = load_json(VIEWER_KEY_BINDINGS_FILE, default=[])
		# A user rebind always wins over the hardcoded defaults below -
		# checked first for that reason.
		if dispatch_bindable_command(
			key_event, key_bindings, self._bindable_commands()
		):
			return
		if event.key() == Qt.Key_Space:
			self._toggle_pause()
			return
		if event.key() == Qt.Key_Left:
			self._player.seek(-5)
			return
		if event.key() == Qt.Key_Right:
			self._player.seek(5)
			return
		if event.key() == Qt.Key_Up:
			self._adjust_volume(5)
			return
		if event.key() == Qt.Key_Down:
			self._adjust_volume(-5)
			return
		if event.key() in (
			Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Backspace
		):
			self._on_close()
			return
		if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
			self._on_switch()
			return
		if not self._nav.run_pane_shortcut(key_event):
			super().keyPressEvent(event)

	def _update_time_label(self):
		# Polled on this Qt timer rather than an mpv property-observer,
		# since observer callbacks fire on mpv's own thread and touching a
		# QLabel from there is unsafe.
		pos = format_time(self._player.time_pos)
		dur = format_time(self._player.duration)
		self._time_label.setText('%s / %s' % (pos, dur))

	def _toggle_pause(self):
		self._player.pause = not self._player.pause
		self._show_osd('Paused' if self._player.pause else 'Playing')

	def _adjust_volume(self, delta):
		self._player.volume = max(0, min(100, self._player.volume + delta))
		save_volume(int(self._player.volume))
		self._show_osd('Volume: %d' % int(self._player.volume))

	def _reset_volume(self):
		self._player.volume = 100
		save_volume(100)
		self._show_osd('Volume: %d' % int(self._player.volume))

	def _toggle_mute(self):
		self._muted = not self._muted
		self._player.mute = self._muted
		save_mute(self._muted)
		self._show_osd('Muted' if self._muted else 'Unmuted')

	def _show_osd(self, text):
		# mpv's own on-screen-display renders over the video and auto-hides -
		# there's no reliable way to overlay a Qt widget on top of the native
		# mpv surface (embedded via wid=, see start_playback). The status bar
		# gets the same text, so video feedback reads the same as every other
		# viewer's even when the OSD is missed or the video is letterboxed.
		self._player.show_text(text, 1000)
		viewer_status(self._nav.pane, text)

	def _restart(self):
		self._player.time_pos = 0
		self._show_osd('Restarted')

	def _bindable_commands(self):
		# Viewer-only pseudo-commands a focused PaneVideoView matches against
		# Viewer Key Bindings.json itself (see keyPressEvent) - not registered
		# DirectoryPaneCommands, not in Core's own Key Bindings.json. Only
		# video_mute has no hardcoded fallback key (palette/user-bind only);
		# the rest mirror the existing Space/Left/Right/Up/Down defaults.
		return {
			'video_toggle_pause': self._toggle_pause,
			'video_volume_up': lambda: self._adjust_volume(5),
			'video_volume_down': lambda: self._adjust_volume(-5),
			'video_mute': self._toggle_mute,
			'video_reset_volume': self._reset_volume,
			'video_seek_forward': lambda: self._player.seek(5),
			'video_seek_backward': lambda: self._player.seek(-5),
			'video_restart': self._restart,
			'viewer_close': self._on_close,
			'viewer_switch_panes': self._on_switch,
			'viewer_open_palette': self._open_palette,
			**self._nav.commands(),
		}

	def _open_palette(self):
		open_viewer_palette(self._get_actions)

	def _get_actions(self):
		return [
			('Play / Pause', self._toggle_pause, '', 'video_toggle_pause'),
			('Restart', self._restart, '', 'video_restart'),
			('Mute / Unmute', self._toggle_mute, '', 'video_mute'),
			(
				'Reset volume', self._reset_volume, '',
				'video_reset_volume'
			),
		] + self._nav.actions() + [
			('Exit viewer', self._on_close, '', 'viewer_close'),
		]

def show_video_viewer(pane, url, focus_view=True):
	"""
	Not @run_in_main_thread (see module docstring) - runs on the calling
	DirectoryPaneCommand's own background thread, so the libmpv download
	below can show a real progress dialog without freezing the app. Only
	_open_video_view, once libmpv/mpv are confirmed available, marshals
	onto the main thread to touch Qt widgets.
	"""
	if sys.platform == 'win32':
		try:
			ensure_libmpv_on_path()
		except Exception as e:
			show_alert('Cannot play video - failed to get libmpv: %s' % e)
			return
	try:
		import mpv as mpv_module
	except (ImportError, OSError) as e:
		# ImportError: python-mpv itself is missing - the Core plugin ships as
		# resource data, so PyInstaller never scans this file for imports and
		# mpv only reaches the freeze via hidden_imports (build/settings/
		# base.json). OSError: mpv.py found, but libmpv is not loadable.
		show_alert('Cannot play video - %s' % e)
		return
	_open_video_view(pane, url, mpv_module, focus_view=focus_view)

@run_in_main_thread
def _open_video_view(pane, url, mpv_module, focus_view=True):
	prepared = begin_new_view(pane)
	if prepared is None:
		return
	widget, bg, _fg = prepared
	path = as_human_readable(url)
	view = PaneVideoView(
		lambda: close_text_viewer(widget),
		lambda: pane.run_command('switch_panes'),
		pane, bg,
	)
	mount_view(pane, widget, view, focus_view=focus_view)
	# Defer starting playback one event-loop tick, same technique mount_view
	# already uses for view.setFocus() - ensures the widget's addWidget/show
	# has actually been processed (real geometry, native window) before mpv
	# grabs its window handle. See PaneVideoView.start_playback for why.
	QTimer.singleShot(0, lambda: view.start_playback(mpv_module, path))
