from fman import ApplicationCommand, DirectoryPaneCommand
from fman.fs import FileSystem, Column
from fman.impl import incognito
from fman.impl.incognito import OFF_MESSAGE, ON_INCOGNITO_CHANGED, ON_MESSAGE
from fman.impl.plugins.plugin import Plugin
from fman.impl.util import filenotfounderror
from fman.impl.util.qt.thread import run_in_main_thread
from fbs_runtime.platform import is_mac
from PyQt5.QtCore import Qt

class BuiltinPlugin(Plugin):
	def __init__(
		self, tour_controller, tutorial_factory, cleanupguide_factory,
		window_chrome, scripting_control, *super_args
	):
		super().__init__(*super_args)

		# We need to define the command classes here so we get access to the
		# scoped variables tour_controller, *_factory, window_chrome and
		# scripting_control. Creating
		# a factory via lambda: ... would not work because fman's current
		# implementation of commands requires them to be actual classes, not
		# lambdas.

		class Tutorial(TourCommand):
			def __init__(self, pane):
				super().__init__(pane, tour_controller, tutorial_factory)

		class CleanupGuide(TourCommand):
			def __init__(self, pane):
				super().__init__(pane, tour_controller, cleanupguide_factory)

		class ToggleTitleBar(ApplicationCommand):
			aliases = ('Toggle title bar',)
			def __call__(self):
				window_chrome.toggle_title_bar(self.window._widget)

		class ToggleStatusBar(ApplicationCommand):
			aliases = ('Toggle status bar',)
			def __call__(self):
				window_chrome.toggle_status_bar(self.window._widget)

		class ToggleIncognito(ApplicationCommand):
			aliases = ('Toggle incognito mode',)
			def __call__(self):
				enabled = not incognito.is_incognito()
				incognito.set_incognito(enabled)
				window = self.window._widget
				window.set_incognito_marker_visible(enabled)
				for pane in self.window.get_panes():
					pane._broadcast(ON_INCOGNITO_CHANGED, enabled)
				window.show_status_message(
					ON_MESSAGE if enabled else OFF_MESSAGE)

		class ToggleScriptingApi(ApplicationCommand):
			aliases = ('Toggle scripting API',)
			@run_in_main_thread
			def __call__(self):
				self.window._widget.show_status_message(
					scripting_control.toggle())

		class TogglePaneStatusLines(ApplicationCommand):
			aliases = ('Toggle pane status lines',)
			def __call__(self):
				window_chrome.pane_status.toggle_lines_visible(
					self.window._widget)

		class TogglePaneMessagesInStatusBar(ApplicationCommand):
			aliases = ('Toggle pane messages in status bar',)
			def __call__(self):
				window_chrome.pane_status.toggle_in_status_bar(
					self.window._widget)

		class ToggleMenuBar(ApplicationCommand):
			aliases = ('Toggle menu bar',)
			def __call__(self):
				window_chrome.toggle_menu_bar(self.window._widget)

		self._register_directory_pane_command(Tutorial)
		self._register_directory_pane_command(CleanupGuide)
		self._register_application_command(ToggleFullscreen)
		self._register_application_command(ToggleTitleBar)
		self._register_application_command(ToggleStatusBar)
		self._register_application_command(ToggleIncognito)
		self._register_application_command(ToggleScriptingApi)
		self._register_application_command(TogglePaneStatusLines)
		self._register_application_command(TogglePaneMessagesInStatusBar)
		# Only Mac has a menu bar to toggle: MainWindow._init_help_menu builds
		# the Help menu from ApplicationContext.help_menu_actions, which is
		# empty everywhere else. Registering it off Mac would put a row in the
		# command palette that cannot do anything. ApplicationCommand has no
		# is_visible(), so gating the registration is the only way to hide it.
		if is_mac():
			self._register_application_command(ToggleMenuBar)
		self._register_file_system(NullFileSystem)
		self._register_column(NullColumn)
	@property
	def name(self):
		return 'Builtin'

class TourCommand(DirectoryPaneCommand):
	def __init__(self, pane, controller, tour_factory):
		super().__init__(pane)
		self._controller = controller
		self._tour_factory = tour_factory
	def __call__(self, step=0):
		self._controller.start(self._tour_factory(self.pane), step)

class ToggleFullscreen(ApplicationCommand):
	@run_in_main_thread
	def __call__(self):
		w = self.window._widget
		w.setWindowState(w.windowState() ^ Qt.WindowFullScreen)

class NullFileSystem(FileSystem):

	scheme = 'null://'

	def get_default_columns(self, path):
		return NullColumn.get_qualified_name(),
	def iterdir(self, path):
		return []
	def is_dir(self, existing_path):
		if not existing_path:
			return True
		raise filenotfounderror(self.scheme + existing_path)
	def exists(self, path):
		return not path

class NullColumn(Column):

	display_name = 'null'

	def get_str(self, url):
		return ''
	def get_sort_value(self, url, is_ascending):
		return None
