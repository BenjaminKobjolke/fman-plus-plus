from fman.impl.util.qt.key_event import QtKeyEvent
from fman.impl.plugins.plugin import ReportExceptions
from fman.impl.view.location_segments import child_on_path
from fman.url import splitscheme
from PyQt5.QtGui import QContextMenuEvent
from threading import Thread
from weakref import WeakValueDictionary

class Controller:
	"""
	The main purpose of this class is to shield the rest of the `plugin`
	implementation from having to know about Qt.
	"""
	def __init__(
		self, plugin_support, nonexistent_shortcut_handler, usage_helper,
		metrics, error_handler
	):
		self._plugin_support = plugin_support
		self._nonexistent_shortcut_handler = nonexistent_shortcut_handler
		self._usage_helper = usage_helper
		self._metrics = metrics
		self._error_handler = error_handler
		self._panes = WeakValueDictionary()
	def register_pane(self, pane_widget, pane):
		self._panes[pane_widget] = pane
		pane_widget.location_changed.connect(self.on_location_changed)
		pane_widget.location_bar_clicked.connect(self.on_location_bar_clicked)
		pane_widget.location_bar_segment_clicked.connect(
			self.on_location_bar_segment_clicked
		)
		pane_widget.selection_changed.connect(self.on_selection_changed)
		self._plugin_support.register_pane(pane)
	def unregister_pane(self, pane_widget, pane):
		self._panes.pop(pane_widget, None)
		self._plugin_support.unregister_pane(pane)
	def on_location_changed(self, pane_widget):
		self._panes[pane_widget]._broadcast('on_path_changed')
	def on_selection_changed(self, pane_widget):
		pane = self._panes.get(pane_widget)
		if pane is not None:
			pane._broadcast('on_selection_changed')
	def on_zoom_step(self, pane_widget, delta):
		pane = self._panes.get(pane_widget)
		if pane is None or not delta:
			return
		if delta > 0:
			command = 'increase_pane_font_size'
		else:
			command = 'decrease_pane_font_size'
		if command in pane.get_commands():
			pane.run_command(command)
	def on_activated(self, pane_widget):
		self._panes[pane_widget]._broadcast('on_activated')
	def on_location_bar_clicked(self, pane_widget):
		past_events = self._metrics.past_events[::]
		self._metrics.track('ClickedLocationBar')
		pane = self._panes[pane_widget]
		if not self._usage_helper.on_location_bar_clicked(pane, past_events):
			pane._broadcast('on_location_bar_clicked')
	def on_location_bar_segment_clicked(self, pane_widget, parent_url: str) -> None:
		pane = self._panes[pane_widget]
		path_before = pane.get_path()
		cursor_target = child_on_path(parent_url, path_before)
		def callback():
			path_now = pane.get_path()
			if path_now == path_before:
				return
			if cursor_target is None:
				pane.move_cursor_home()
				return
			cursor_dest = splitscheme(path_now)[0] + \
				splitscheme(cursor_target)[1]
			try:
				pane.place_cursor_at(cursor_dest)
			except ValueError:
				pane.move_cursor_home()
		try:
			pane.set_path(parent_url, callback)
		except FileNotFoundError:
			pass
	def handle_shortcut(self, pane_widget, qkeyevent):
		pane = self._panes[pane_widget]
		key_event = QtKeyEvent(qkeyevent.key(), qkeyevent.modifiers())
		for key_binding in self._plugin_support.get_sanitized_key_bindings():
			keys = key_binding['keys']
			if key_event.matches(keys[0]):
				cmd_name = key_binding['command']
				args = key_binding.get('args', {})
				if cmd_name in pane.get_commands():
					pane.run_command(cmd_name, args)
				else:
					self._plugin_support.run_application_command(cmd_name, args)
				return True
		return False
	def handle_nonexistent_shortcut(self, pane_widget, qkeyevent):
		is_single_char = qkeyevent.text() and not qkeyevent.modifiers()
		if is_single_char:
			return False
		pane = self._panes[pane_widget]
		key_event = QtKeyEvent(qkeyevent.key(), qkeyevent.modifiers())
		return self._nonexistent_shortcut_handler(key_event, pane)
	def on_doubleclicked(self, pane_widget, file_path):
		past_events = self._metrics.past_events[::]
		self._metrics.track('DoubleclickedFile')
		pane = self._panes[pane_widget]
		if not self._usage_helper.on_doubleclicked(pane, past_events):
			pane._broadcast('on_doubleclicked', file_path)
	def on_file_renamed(self, pane_widget, file_url, new_name):
		self._metrics.track('RenamedFile')
		pane = self._panes[pane_widget]
		callback = pane._take_edit_name_callback()
		if callback is None:
			pane._broadcast('on_name_edited', file_url, new_name)
		else:
			# Callbacks can do file IO and show dialogs, like listener events.
			Thread(
				target=self._run_edit_name_callback,
				args=(callback, file_url, new_name), daemon=True
			).start()
	def _run_edit_name_callback(self, callback, file_url, new_name):
		with ReportExceptions(
			self._error_handler,
			'DirectoryPane.edit_name(...) callback raised error.'
		):
			callback(file_url, new_name)
	def on_files_dropped(self, pane_widget, *args):
		self._metrics.track('DroppedFile')
		self._panes[pane_widget]._broadcast('on_files_dropped', *args)
	def on_context_menu(self, pane_widget, event, file_under_mouse):
		if event.reason() == QContextMenuEvent.Mouse:
			via = 'Mouse'
		elif event.reason() == QContextMenuEvent.Keyboard:
			via = 'Keyboard'
		else:
			assert event.reason() == QContextMenuEvent.Other, event.reason()
			via = 'Other'
		past_events = self._metrics.past_events[::]
		self._metrics.track('OpenedContextMenu', {'via': via})
		pane = self._panes[pane_widget]
		if self._usage_helper.on_context_menu(pane, via, past_events):
			return []
		return self._plugin_support.get_context_menu(pane, file_under_mouse)
