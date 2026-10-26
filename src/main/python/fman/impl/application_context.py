from fbs_runtime import application_context as fbs_appctxt, PUBLIC_SETTINGS
from fbs_runtime.application_context import cached_property
from fbs_runtime.application_context.PyQt5 import ApplicationContext
from fbs_runtime.excepthook import StderrExceptionHandler
from fbs_runtime.excepthook.sentry import SentryExceptionHandler
from fbs_runtime.platform import is_mac
from fman import APP_NAME, PLATFORM, DATA_DIRECTORY, Window
from fman.impl.controller import Controller
from fman.impl.console_log import get_console_log, install_stream_capture
from fman.impl.font_database import FontDatabase
from fman.impl.metrics import Metrics, ServerBackend, AsynchronousMetrics, \
	LoggingBackend
from fman.impl.model.icon_provider import GnomeFileIconProvider, \
	GnomeNotAvailable, IconProvider
from fman.impl.model.icon_set import load_icon_set
from fman.impl.nonexistent_shortcut_handler import NonexistentShortcutHandler
from fman.impl.plugins import PluginSupport, CommandCallback, PluginFactory
from fman.impl.plugins.builtin import BuiltinPlugin, NullFileSystem
from fman.impl.plugins.command_registry import PaneCommandRegistry, \
	ApplicationCommandRegistry
from fman.impl.plugins.config import Config
from fman.impl.plugins.context_menu import ContextMenuProvider
from fman.impl.plugins.discover import find_plugin_dirs
from fman.impl.plugins.error import PluginErrorHandler
from fman.impl.plugins.key_bindings import KeyBindings
from fman.impl.plugins.mother_fs import MotherFileSystem
from fman.impl.viewers import ViewerRegistry
from fman.impl.session import SessionManager
from fman.impl.scripting.actions import ScriptingActions
from fman.impl.scripting.automation import AutomationActions
from fman.impl.scripting.config import ScriptingApiConfig
from fman.impl.scripting.control import ScriptingApiControl
from fman.impl.scripting.server import ScriptingServer
from fman.impl.single_instance import SingleInstance, server_name_for, \
	open_paths_in_running_instance
from fman.impl.theme import Theme
from fman.impl.theme_controller import ThemeController
from fman.impl.window_chrome import WindowChrome
from fman.impl.themes import DEFAULT_THEME, THEME_SETTING, \
	build_main_window_palette, build_palette, \
	build_progress_bar_palette, build_tokens, list_themes, load_theme
from fman.impl.onboarding import TourController
from fman.impl.onboarding.cleanup_guide import CleanupGuide
from fman.impl.onboarding.tutorial import Tutorial
from fman.impl.usage_helper import UsageHelper
from fman.impl.update_check import UpdateCheckTimer
from fman.impl.util import os_
from fman.impl.util.path import make_absolute
from fman.impl.util.qt import connect_once
from fman.impl.util.settings import Settings
from fman.impl.view import ProxyStyle
from fman.impl.widgets import MainWindow, Application
from os import makedirs, getcwd
from os.path import dirname, join
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QStyleFactory, QFileIconProvider

import fman
import json
import logging
import os
import sys

def get_application_context():
	return fbs_appctxt.get_application_context(
		DevelopmentApplicationContext, FrozenApplicationContext
	)

class DevelopmentApplicationContext(ApplicationContext):
	def __init__(self):
		super().__init__()
		self._main_window = None
		self._demo_mode = False
	def run(self):
		self.init_logging()
		if '--automation-demo' in sys.argv:
			return self._run_demo()
		if self.single_instance_enabled:
			# Touch self.app first: QLocalSocket needs a QApplication instance.
			_ = self.app
			abs_paths = [make_absolute(a, getcwd()) for a in sys.argv[1:]]
			if self.single_instance.try_forward(abs_paths):
				return 0
			self.single_instance.start_listening()
		self._start_metrics()
		self._load_plugins()
		if ScriptingApiConfig.from_settings(self.local_settings).enabled:
			try:
				self.scripting_control.start()
			except OSError:
				# The control logged the bind failure; fman remains usable.
				pass
		self.session_manager.show_main_window(self.window)
		return self.app.exec_()
	def _run_demo(self):
		# Play a scripted demo for the automated-application-screenshots tool
		# (see fman.impl.demo). Bypasses single-instance + onboarding so the
		# recording is a clean, deterministic run.
		log = logging.getLogger(__name__)
		try:
			from automated_screenshot_connector import DemoClient, \
				localize_script, parse_demo_args
			from fman.impl.demo import DemoPlayer
			from fman.impl.demo_scripts import DEMO_OPACITY, demo_ids, \
				get_script
		except ImportError:
			log.error(
				'Demo mode needs the automated-screenshot-connector. Install '
				'it with: pip install -r requirements/windows-debug.txt'
			)
			return 1
		options, leftover = parse_demo_args(sys.argv[1:])
		# Built here rather than looked up, because the themes demo's steps
		# depend on which themes are installed. Before _load_plugins, so an
		# unknown id still fails in a second.
		script = get_script(options.demo, list_themes(self.bundled_theme_dirs))
		if script is None:
			log.error(
				'Unknown demo id %s (available: %s)', options.demo, demo_ids()
			)
			return 2
		# session.py reads sys.argv[1:] raw to open pane paths, so strip the
		# --automation-demo* flags and leave only the folder arguments.
		sys.argv[1:] = leftover
		self._demo_mode = True
		self._load_plugins()
		self.session_manager.show_main_window(self.window)
		# A recording must not inherit the recordist's window opacity, nor
		# whatever a previous take left in the demo profile: every chapter
		# starts at the same known value, and the overview's opacity chapter
		# is written against it.
		self.main_window.setWindowOpacity(DEMO_OPACITY)
		if options.demo_width is not None and options.demo_height is not None:
			# show_main_window may maximize (settings-less run) or restore old
			# geometry; the recording needs the size the tool asked for.
			self.main_window.showNormal()
			self.main_window.resize(options.demo_width, options.demo_height)
			# So a take does not depend on where the recordist last left the
			# window. Same method the Center window command runs.
			self.main_window.center_on_screen()
		script = localize_script(script, dict(options.demo_texts))
		client = DemoClient(options.demo_port)
		player = DemoPlayer(
			self.main_window, client, script, int(self.main_window.winId())
		)
		player.start()
		return self.app.exec_()
	@cached_property
	def single_instance_enabled(self):
		return self.local_settings.get('single_instance', True)
	@cached_property
	def single_instance(self):
		return SingleInstance(
			server_name_for(DATA_DIRECTORY), self._on_single_instance_message
		)
	def _on_single_instance_message(self, abs_paths):
		# Runs on the Qt main thread via QLocalServer.newConnection.
		open_paths_in_running_instance(
			self.main_window, self.plugin_support, self.session_manager,
			abs_paths
		)
	def init_logging(self):
		install_stream_capture(get_console_log())
		logging.basicConfig()
	def _start_metrics(self):
		self.metrics.initialize(callback=self._on_metrics_initialised)
		self.metrics.track('StartedFman')
	def _on_metrics_initialised(self):
		# Overwritten by FrozenApplicationContext below.
		pass
	def _load_plugins(self):
		fman.FMAN_VERSION = self.fman_version
		plugin_dirs = find_plugin_dirs(
			self.get_resource('Plugins'),
			join(DATA_DIRECTORY, 'Plugins', 'Third-party'),
			join(DATA_DIRECTORY, 'Plugins', 'User')
		)
		settings_plugin = plugin_dirs[-1]
		makedirs(settings_plugin, exist_ok=True)
		# Ensure main_window is instantiated before plugin_support, or else
		# plugin_support gets instantiated twice:
		_ = self.main_window
		for plugin_dir in plugin_dirs:
			self.plugin_support.load_plugin(plugin_dir)
		self.theme.enable_updates()
	@property
	def fman_version(self):
		return PUBLIC_SETTINGS['version']
	def on_main_window_shown(self):
		if self._demo_mode:
			# No tutorial during a recording.
			return
		self.update_check_timer.start()
		if self.session_manager.is_first_run:
			pane = self.plugin_support.get_panes()[0]
			tutorial = self.tutorial_factory(pane)
			self.tour_controller.start(tutorial)
	def on_main_window_close(self):
		self.session_manager.on_close(self.main_window)
	def on_quit(self):
		self.scripting_control.stop()
		self.config.on_quit()
		if self.metrics_logging_enabled:
			log_dir = dirname(self._get_metrics_json_path())
			log_file_path = join(log_dir, 'Metrics.log')
			self.metrics_backend.flush(log_file_path)
	@cached_property
	def app(self):
		result = Application([sys.argv[0]])
		result.setOrganizationName('fman.io')
		result.setOrganizationDomain('fman.io')
		result.setApplicationName('fman')
		result.setApplicationDisplayName(APP_NAME)
		result.setStyle(self.style)
		result.setPalette(self.palette)
		result.aboutToQuit.connect(self.on_quit)
		# We need to instantiate this somewhere. So why not here:
		_ = self.mac_clipboard_fix
		return result
	@cached_property
	def mac_clipboard_fix(self):
		if is_mac():
			from fman.impl.mac_clipboard_fix import MacClipboardFix
			return MacClipboardFix()
	@cached_property
	def command_callback(self):
		return CommandCallback(self.metrics)
	@cached_property
	def exception_handlers(self):
		return [self.plugin_error_handler, StderrExceptionHandler()]
	@property
	def main_window(self):
		if self._main_window is None:
			self._main_window = MainWindow(
				self.app, self.help_menu_actions, self.theme,
				self.progress_bar_palette, self.mother_fs, NullFileSystem.scheme
			)
			# Resolve the cyclic dependency main_window <-> controller
			self._main_window.set_controller(self.controller)
			self._main_window.setWindowTitle(self._get_main_window_title())
			self._main_window.setPalette(self.main_window_palette)
			# Before show(): Qt keeps the value until the native window is
			# created and applies it there, so the window never flashes
			# opaque the way a post-show hook would make it.
			self._main_window.setWindowOpacity(
				self.theme_controller.get_opacity()
			)
			# Likewise the saved icon size: MainWindow starts at None (Qt's
			# own 16px) and is only told otherwise by set_icon_size(...) and
			# set_theme(...), neither of which runs at startup. Without this
			# the size would last the session but not survive a restart.
			self._main_window.set_file_list_icon_size(
				self.theme_controller.get_icon_size()
			)
			# Likewise the theme's background images. The window has no
			# panes yet - the session opens them - so this only stores
			# them; add_pane is what hands each pane its own.
			self._main_window.set_backgrounds(
				self.theme_controller.get_backgrounds()
			)
			# Before show() for the same reason as the opacity above, and a
			# stronger one: setWindowFlags on a visible window recreates the
			# native one - see fman.impl.window_chrome.
			self.window_chrome.apply(self._main_window)
			connect_once(self._main_window.shown, self.on_main_window_shown)
			connect_once(
				self._main_window.shown,
				lambda: self.plugin_error_handler.on_main_window_shown(
					self.main_window
				)
			)
			self._main_window.closed.connect(self.on_main_window_close)
			self.app.set_main_window(self._main_window)
			if PLATFORM == 'Windows':
				from fman.impl.build_shutdown import BuildShutdownFilter
				# Kept on self: Qt does not own the filter, so Python's
				# garbage collector would otherwise delete it.
				self._build_shutdown_filter = BuildShutdownFilter(
					self._main_window, self.app.exit
				)
				self.app.installNativeEventFilter(self._build_shutdown_filter)
		return self._main_window
	def _get_main_window_title(self):
		return APP_NAME
	@cached_property
	def help_menu_actions(self):
		if is_mac():
			def app_command(name):
				return lambda _: \
					self.plugin_support.run_application_command(name)
			def directory_pane_command(name):
				def result(_):
					active_pane = self.plugin_support.get_active_pane()
					if active_pane:
						active_pane.run_command(name)
				return result
			return [
				('Keyboard shortcuts', 'F1', app_command('help')),
				(
					'Command Palette', 'Ctrl+Shift+P',
					directory_pane_command('command_palette')
				),
				('Tutorial', '', directory_pane_command('tutorial'))
			]
		else:
			return []
	@cached_property
	def font_database(self):
		return FontDatabase()
	@cached_property
	def key_bindings(self):
		return KeyBindings()
	@cached_property
	def builtin_plugin(self):
		return BuiltinPlugin(
			self.tour_controller, self.tutorial_factory,
			self.cleanupguide_factory, self.window_chrome,
			self.scripting_control,
			self.plugin_error_handler,
			self.application_command_registry, self.pane_command_registry,
			self.key_bindings, self.mother_fs, self.viewer_registry,
			self.window
		)
	@cached_property
	def viewer_registry(self):
		return ViewerRegistry()
	@cached_property
	def window_chrome(self):
		return WindowChrome(self.local_settings)
	@cached_property
	def scripting_control(self):
		return ScriptingApiControl(
			self.local_settings,
			self._get_local_data_file('ScriptingApiToken.txt'),
			lambda config, token: ScriptingServer(
				config, token,
				ScriptingActions(self.plugin_support, self.main_window),
				AutomationActions(self.main_window, self.plugin_support),
			),
		)
	@cached_property
	def mother_fs(self):
		# Resolve the cyclic dependency MotherFileSystem <-> IconProvider:
		result = MotherFileSystem(None)
		result._icon_provider = self._get_icon_provider(result)
		return result
	@cached_property
	def icon_provider(self):
		# The one MotherFileSystem was wired to - see mother_fs, which
		# resolves the cycle between the two. ThemeController swaps its icon
		# set from here when the theme or the user's choice changes.
		return self.mother_fs._icon_provider
	def _get_icon_provider(self, fs):
		try:
			qt_icon_provider = GnomeFileIconProvider()
		except GnomeNotAvailable:
			qt_icon_provider = QFileIconProvider()
		icons_dir = self._get_local_data_file('Cache', 'Icons')
		makedirs(icons_dir, exist_ok=True)
		return IconProvider(
			qt_icon_provider, fs, icons_dir,
			load_icon_set(self.theme_controller.get_icon_set(), self.icon_dirs),
			self.theme_controller.get_icon_color()
		)
	@cached_property
	def config(self):
		return Config(PLATFORM)
	@cached_property
	def tour_controller(self):
		return TourController()
	@cached_property
	def tutorial_factory(self):
		return lambda pane: Tutorial(
			self.session_manager.is_first_run, self.main_window, pane, self.app,
			self.command_callback, self.metrics
		)
	@cached_property
	def cleanupguide_factory(self):
		return lambda pane: CleanupGuide(
			self.main_window, pane, self.app, self.command_callback,
			self.metrics
		)
	@cached_property
	def plugin_support(self):
		return PluginSupport(
			self.plugin_factory, self.application_command_registry,
			self.key_bindings, self.context_menu_provider, self.config,
			self.builtin_plugin
		)
	@cached_property
	def update_check_timer(self):
		return UpdateCheckTimer(self.plugin_support, QTimer(self.app))
	@cached_property
	def plugin_factory(self):
		return PluginFactory(
			self.config, self.theme, self.font_database,
			self.plugin_error_handler, self.application_command_registry,
			self.pane_command_registry, self.key_bindings,
			self.context_menu_provider, self.mother_fs, self.viewer_registry,
			self.window
		)
	@cached_property
	def application_command_registry(self):
		return ApplicationCommandRegistry(
			self.window, self.plugin_error_handler, self.command_callback
		)
	@cached_property
	def pane_command_registry(self):
		return PaneCommandRegistry(
			self.plugin_error_handler, self.command_callback
		)
	@cached_property
	def context_menu_provider(self):
		return ContextMenuProvider(
			self.pane_command_registry, self.application_command_registry,
			self.key_bindings
		)
	@cached_property
	def plugin_error_handler(self):
		return PluginErrorHandler(
			self.app, get_console_log(), self._open_console_from_error
		)
	def _open_console_from_error(self):
		pane = self.plugin_support.get_active_pane()
		if pane is None:
			pane = self.main_window.get_panes()[0]
		pane.run_command('show_console')
	@cached_property
	def controller(self):
		return Controller(
			self.plugin_support, self.nonexistent_shortcut_handler,
			self.usage_helper, self.metrics
		)
	@cached_property
	def nonexistent_shortcut_handler(self):
		settings = Settings(self._get_local_data_file('Dialogs.json'))
		return NonexistentShortcutHandler(
			self.main_window, settings, self.metrics
		)
	@cached_property
	def usage_helper(self):
		return UsageHelper(self.session_manager.is_first_run)
	@cached_property
	def metrics(self):
		json_path = self._get_metrics_json_path()
		metrics = Metrics(
			json_path, self.metrics_backend, PLATFORM, self.fman_version
		)
		return AsynchronousMetrics(metrics)
	def _get_metrics_json_path(self):
		return self._get_local_data_file('Metrics.json')
	@cached_property
	def metrics_logging_enabled(self):
		return self._read_metrics_logging_enabled()
	def _read_metrics_logging_enabled(self):
		json_path = self._get_metrics_json_path()
		try:
			with open(json_path, 'r') as f:
				data = json.load(f)
		except (FileNotFoundError, ValueError):
			return False
		else:
			try:
				return data.get('logging_enabled', False)
			except AttributeError:
				return False
	@cached_property
	def metrics_backend(self):
		metrics_url = PUBLIC_SETTINGS['server_url'] + '/metrics'
		backend = ServerBackend(metrics_url + '/users', metrics_url + '/events')
		if self.metrics_logging_enabled:
			backend = LoggingBackend(backend)
		return backend
	@cached_property
	def local_settings(self):
		# Not Core Settings.json: the palette below is built when the
		# QApplication is created, long before any plugin (and thus
		# fman.load_json) exists. One shared instance, so that flushing the
		# theme cannot drop another setting read from the same file.
		return Settings(self._get_local_data_file('Settings.json'))
	@cached_property
	def bundled_theme_dirs(self):
		# Separate from theme_dirs because the themes demo records *these*
		# only: run_fman_demo.bat mirrors the recordist's own Themes folder
		# into the demo profile (so their custom theme resolves), and a
		# private theme must not end up in the README's themes GIF.
		try:
			return [self.get_resource('Themes')]
		except FileNotFoundError:
			return []
	@cached_property
	def theme_dirs(self):
		return self.bundled_theme_dirs + [join(DATA_DIRECTORY, 'Themes')]
	@cached_property
	def icon_dirs(self):
		# Same shape and same "later dirs win" rule as theme_dirs, so a user
		# icon set shadows a bundled one of the same name. There is no
		# bundled-only variant: the demos do not switch icon sets, which is
		# the only reason bundled_theme_dirs exists separately.
		try:
			bundled = [self.get_resource('Icons')]
		except FileNotFoundError:
			bundled = []
		return bundled + [join(DATA_DIRECTORY, 'Icons')]
	@cached_property
	def theme_colors(self):
		return load_theme(
			self.local_settings.get(THEME_SETTING, DEFAULT_THEME),
			self.theme_dirs
		)
	@cached_property
	def theme_tokens(self):
		# The colors plus the font family, which is a stylesheet token but
		# not a color. Read through theme_controller so the user's own
		# font wins over the theme's at startup too, not only after a
		# switch.
		return build_tokens(
			self.theme_colors, self.theme_controller.get_font()
		)
	@cached_property
	def theme_controller(self):
		return ThemeController(self)
	@cached_property
	def palette(self):
		return build_palette(self.theme_colors)
	@cached_property
	def main_window_palette(self):
		return build_main_window_palette(self.theme_colors)
	@cached_property
	def progress_bar_palette(self):
		return build_progress_bar_palette(self.theme_colors)
	@cached_property
	def session_manager(self):
		settings = Settings(self._get_local_data_file('Session.json'))
		return SessionManager(
			settings, self.mother_fs, self.plugin_error_handler,
			self.fman_version
		)
	@cached_property
	def theme(self):
		qss_files = [self.get_resource('styles.qss')]
		try:
			os_styles = self.get_resource('os_styles.qss')
		except FileNotFoundError:
			pass
		else:
			qss_files.append(os_styles)
		return Theme(self.app, qss_files, self.theme_tokens)
	@cached_property
	def style(self):
		base_style = None
		base_style_name = os.environ.get('QT_QPA_PLATFORMTHEME')
		if base_style_name:
			base_style = QStyleFactory.create(base_style_name)
		if not base_style:
			base_style = QStyleFactory.create('Fusion')
		return ProxyStyle(base_style)
	@cached_property
	def window(self):
		return Window(self.main_window, self.pane_command_registry)
	def _get_local_data_file(self, *rel_path):
		return join(DATA_DIRECTORY, 'Local', *rel_path)

class FrozenApplicationContext(DevelopmentApplicationContext):
	def init_logging(self):
		install_stream_capture(get_console_log())
		logging.basicConfig(level=logging.CRITICAL)
	def on_main_window_shown(self):
		if PLATFORM == 'Linux':
			"""
			PyInstaller sets LD_LIBRARY_PATH to /opt/fman. Processes we spawn,
			be it via Popen(...) or QDesktopServices.openUrl(...), inherit this
			value. This leads to problems, especially when the app we launch is
			based on Qt. The reason is that the OS then attempts to load our
			libraries, which are most likely incompatible with those of the app.
			An example where this happens is VLC, which errors out with 'This
			application failed to start because it could not find or load the Qt
			platform plugin "xcb"'. Plugin developers have also encountered this
			unexpected behaviour when trying to launch apps.

			To fix the problem, we restore LD_LIBRARY_PATH to its original value
			here. According to the docs [1], PyInstaller stores this value in a
			separate environment variable.

			A drawback of unsetting the environment variable here is that
			libraries from PyInstaller's search path cannot be loaded after this
			method was called. In other words, we assume that all required
			libraries have been loaded once we reach here. This assumption may
			turn out to be wrong in the future.

			[1]: http://pyinstaller.readthedocs.io/en/stable/runtime-information.html#ld-library-path-libpath-considerations
			"""
			lp_orig = os.environ.pop('LD_LIBRARY_PATH_ORIG', None)
			if lp_orig is not None:
				os.environ['LD_LIBRARY_PATH'] = lp_orig
			else:
				os.environ.pop('LD_LIBRARY_PATH', None)
		# Similarly to above, PyInstaller sets various QT_... environment
		# variables. This can confuse Qt-based apps which we launch via
		# Popen(...) or QDesktopServices.openUrl(...). An example of this is
		# XnViewMP [1]. Unset the variables here to avoid this. Again, this
		# assumes that by the time we reach here, all required Qt libraries have
		# been loaded.
		# 1: https://github.com/fman-users/fman/issues/570
		delete = [var for var in os.environ if var.startswith('QT_')]
		for var in delete:
			del os.environ[var]
		if PLATFORM == 'Windows':
			# PyInstaller's bootloader calls SetDllDirectory(...\_internal), and
			# processes we spawn inherit it. They then load our DLLs (eg.
			# VCRUNTIME140.dll) instead of their own, which also keeps
			# target\fman locked so the next build cannot replace it. Restore
			# the default search order, under the same assumption as above.
			import ctypes
			ctypes.windll.kernel32.SetDllDirectoryW(None)
		super().on_main_window_shown()
	@cached_property
	def exception_handlers(self):
		result = super().exception_handlers
		result.append(self.sentry_exception_handler)
		return result
	@cached_property
	def sentry_exception_handler(self):
		return SentryExceptionHandler(
			PUBLIC_SETTINGS['sentry_dsn'],
			self.fman_version,
			PUBLIC_SETTINGS['environment'],
			callback=self._on_sentry_init
		)
	def _on_sentry_init(self):
		scope = self.sentry_exception_handler.scope
		scope.set_extra('os_name', os_.name())
		scope.set_extra('os_version', os_.version())
		scope.set_extra('os_distribution', os_.distribution())
	def _on_metrics_initialised(self):
		self.sentry_exception_handler.scope.user = {
			'id': self.metrics.get_user()
		}
