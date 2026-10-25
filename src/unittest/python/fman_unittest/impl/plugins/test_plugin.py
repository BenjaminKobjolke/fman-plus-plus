from fman import DirectoryPaneListener
from fman.fs import FileSystem
from fman.impl.plugins.plugin import _get_command_name, \
	get_command_class_name, ExternalPlugin, FileSystemWrapper, ListenerWrapper
from fman_unittest.impl.plugins import StubErrorHandler
from threading import Event, current_thread
from types import ModuleType
from unittest import TestCase

import sys

class IncognitoListenerTest(TestCase):
	def test_listener_wrapper_dispatches_on_activated_on_thread(self):
		called = Event()
		calls = []
		caller_thread = current_thread()

		class Listener(DirectoryPaneListener):
			def on_activated(self):
				calls.append(current_thread())
				called.set()

		wrapper = ListenerWrapper(Listener(None), StubErrorHandler())
		wrapper.on_activated()

		self.assertTrue(called.wait(1))
		self.assertIsNot(caller_thread, calls[0])

	def test_listener_wrapper_dispatches_on_incognito_changed_on_thread(self):
		called = Event()
		calls = []
		caller_thread = current_thread()

		class Listener(DirectoryPaneListener):
			def on_incognito_changed(self, enabled):
				calls.append((enabled, current_thread()))
				called.set()

		wrapper = ListenerWrapper(Listener(None), StubErrorHandler())
		wrapper.on_incognito_changed(True)

		self.assertTrue(called.wait(1))
		self.assertEqual(True, calls[0][0])
		self.assertIsNot(caller_thread, calls[0][1])

	def test_base_listener_callback_is_noop(self):
		self.assertIsNone(DirectoryPaneListener(None).on_incognito_changed(True))

class GetCommandNameTest(TestCase):
	def test_single_letter(self):
		self.assertEqual('c', _get_command_name('C'))
	def test_single_word(self):
		self.assertEqual('copy', _get_command_name('Copy'))
	def test_two_words(self):
		self.assertEqual(
			'open_terminal', _get_command_name('OpenTerminal')
		)
	def test_three_words(self):
		self.assertEqual(
			'move_cursor_up', _get_command_name('MoveCursorUp')
		)
	def test_two_consecutive_upper_case_chars(self):
		self.assertEqual('get_url', _get_command_name('GetURL'))

class GetCommandClassNameTest(TestCase):
	def test_is_inverse_of_get_command_name(self):
		for test_string in ('C', 'Copy', 'OpenTerminal', 'MoveCursorUp'):
			result = get_command_class_name(_get_command_name(test_string))
			self.assertEqual(test_string, result)

class UnregisterPackageTest(TestCase):
	def test_package_already_gone(self):
		# Two plugins may ship packages of the same name (eg. a plugin that
		# is installed both under Third-party/ and User/). The second load
		# overwrites the first one's sys.modules entry, so on unload only the
		# first del succeeds. The second must not abort the whole reload.
		package = ModuleType('fman_unittest_package_that_is_not_loaded')
		ExternalPlugin._unregister_package(None, package)

class ReportIfPackageNameTakenTest(TestCase):
	def test_reports_clash(self):
		other = ModuleType('fman_unittest_clashing_package')
		other.__file__ = r'C:\Plugins\Other\pkg\__init__.py'
		sys.modules[other.__name__] = other
		try:
			self._plugin._report_if_package_name_taken(
				other.__name__, r'C:\Plugins\Mine\pkg\__init__.py'
			)
		finally:
			del sys.modules[other.__name__]
		message, = self._error_handler.error_messages
		self.assertIn('fman_unittest_clashing_package', message)
		self.assertIn(r'C:\Plugins\Other\pkg\__init__.py', message)
		self.assertIn(r'C:\Plugins\Mine\pkg\__init__.py', message)
	def test_name_is_free(self):
		self._plugin._report_if_package_name_taken(
			'fman_unittest_package_that_is_not_loaded', 'irrelevant'
		)
		self.assertEqual([], self._error_handler.error_messages)
	def setUp(self):
		super().setUp()
		self._error_handler = StubErrorHandler()
		# ExternalPlugin's constructor only stores its arguments, so the
		# collaborators this test does not exercise can be None.
		self._plugin = ExternalPlugin(
			r'C:\Plugins\Mine', None, None, None, None,
			self._error_handler, None, None, None, None, None, None
		)

class FileSystemWrapperTest(TestCase):
	def test_iterdir_not_implemented(self):

		class IterdirNotImplemented(FileSystem):
			scheme = 'noiterdir://'

		wrapper = self._wrap(IterdirNotImplemented)
		self.assertEqual([], list(wrapper.iterdir('')))
		self._expect_error(
			"Error: FileSystem 'IterdirNotImplemented' does not implement "
			"iterdir(...)."
		)
	def test_iterdir_none(self):
		self._test_iterdir_error(
			lambda _: None,
			"Error: FS.iterdir(...) returned None instead of an iterable such "
			"as ['a.txt', 'b.jpg']."
		)
	def test_iterdir_number(self):
		self._test_iterdir_error(
			lambda _: 2,
			"Error: FS.iterdir(...) returned 2 instead of an iterable such "
			"as ['a.txt', 'b.jpg']."
		)
	def test_iterdir_non_string(self):
		def iterdir(_):
			yield from range(5)
		self._test_iterdir_error(
			iterdir,
			"Error: FS.iterdir(...) yielded 0 instead of a string such as "
			"'file.txt'."
		)
	def test_iterdir_raising_error(self):
		def iterdir(_):
			raise ValueError()
		self._test_iterdir_error(iterdir, "FileSystem 'FS' raised error.")
	def test_get_default_columns_nonexistent(self):
		self._test_get_default_columns_error(
			lambda _: ('Name',),
			"Error: FS.get_default_columns(...) returned a column that does "
			"not exist: 'Name'. Should have been one of: 'core.Name', "
			"'core.Size', 'core.Modified'."
		)
	def _test_iterdir_error(self, iterdir, expected_error):
		class FS(FileSystem):
			scheme = 'scheme://'
			def iterdir(self, path):
				return iterdir(path)
		wrapper = self._wrap(FS)
		self.assertEqual([], list(wrapper.iterdir('')))
		self._expect_error(expected_error)
	def _test_get_default_columns_error(self, get_default_cols, expected_error):
		class FS(FileSystem):
			scheme = 'scheme://'
			def get_default_columns(self, path):
				return get_default_cols(path)
		wrapper = self._wrap(FS)
		self.assertEqual(('core.Name',), wrapper.get_default_columns(''))
		self._expect_error(expected_error)
	def _wrap(self, fs_class):
		fs = StubMotherFileSystem(['core.Name', 'core.Size', 'core.Modified'])
		return FileSystemWrapper(fs_class(), fs, self._error_handler)
	def _expect_error(self, error_message):
		self.assertEqual([error_message], self._error_handler.error_messages)
	def setUp(self):
		super().setUp()
		self._error_handler = StubErrorHandler()

class StubMotherFileSystem:
	def __init__(self, columns):
		self._columns = columns
	def get_registered_column_names(self):
		return self._columns
