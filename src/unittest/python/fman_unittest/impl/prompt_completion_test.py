"""Isolated Qt tests for Tab completion in destination prompts."""

from fman.impl.prompt_completion import PromptTabCompletion
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QLineEdit
from threading import Event, get_ident
from unittest import TestCase


class PromptTabCompletionTest(TestCase):
	def test_tab_applies_first_match_and_places_cursor_at_end(self):
		line_edit, completion = self._completion(lambda text: ['alpha/', 'atom/'])
		self.assertTrue(self._tab(completion))
		self._wait_for(lambda: line_edit.text() == 'alpha/')
		self.assertEqual(len(line_edit.text()), line_edit.cursorPosition())

	def test_tab_cycles_wraps_and_shift_tab_goes_back(self):
		line_edit, completion = self._completion(lambda text: ['alpha/', 'atom/'])
		self._tab(completion)
		self._wait_for(lambda: line_edit.text() == 'alpha/')
		self._tab(completion)
		self.assertEqual('atom/', line_edit.text())
		self._tab(completion)
		self.assertEqual('alpha/', line_edit.text())
		self._tab(completion, Qt.ShiftModifier, Qt.Key_Backtab)
		self.assertEqual('atom/', line_edit.text())

	def test_typing_after_completion_starts_a_new_round(self):
		calls = []
		def get_completions(text):
			calls.append(text)
			return [text + 'one/']
		line_edit, completion = self._completion(get_completions)
		self._tab(completion)
		self._wait_for(lambda: line_edit.text() == 'one/')
		line_edit.setText('br')
		self._tab(completion)
		self._wait_for(lambda: line_edit.text() == 'brone/')
		self.assertEqual(['', 'br'], calls)

	def test_result_is_dropped_when_text_changed_while_loading(self):
		started, release = Event(), Event()
		def get_completions(text):
			started.set()
			release.wait(2)
			return ['stale/']
		line_edit, completion = self._completion(get_completions)
		self._tab(completion)
		self.assertTrue(started.wait(1))
		line_edit.setText('new')
		release.set()
		self._wait_for(lambda: not completion._in_flight)
		self.assertEqual('new', line_edit.text())

	def test_no_matches_leaves_text_unchanged(self):
		line_edit, completion = self._completion(lambda text: [])
		line_edit.setText('missing')
		self._tab(completion)
		self._wait_for(lambda: not completion._in_flight)
		self.assertEqual('missing', line_edit.text())

	def test_callback_error_is_logged_and_leaves_text_unchanged(self):
		def fail(_text):
			raise ValueError('unexpected callback failure')
		line_edit, completion = self._completion(fail)
		line_edit.setText('missing')
		with self.assertLogs('fman.impl.prompt_completion', level='ERROR') as logs:
			self._tab(completion)
			self._wait_for(lambda: not completion._in_flight)
		self.assertIn('unexpected callback failure', logs.output[0])
		self.assertEqual('missing', line_edit.text())

	def test_tab_is_consumed(self):
		_, completion = self._completion(lambda text: [])
		self.assertTrue(self._tab(completion))

	def test_callable_runs_off_the_gui_thread(self):
		threads = []
		line_edit, completion = self._completion(
			lambda text: threads.append(get_ident()) or ['alpha/']
		)
		self._tab(completion)
		self._wait_for(lambda: line_edit.text() == 'alpha/')
		self.assertNotEqual(get_ident(), threads[0])

	def _completion(self, get_completions):
		line_edit = QLineEdit()
		line_edit.show()
		self.addCleanup(line_edit.close)
		completion = PromptTabCompletion(line_edit, get_completions)
		return line_edit, completion

	def _tab(self, completion, modifiers=Qt.NoModifier, key=Qt.Key_Tab):
		event = QKeyEvent(QEvent.KeyPress, key, modifiers)
		return completion.eventFilter(completion._line_edit, event)

	def _wait_for(self, predicate):
		for _ in range(200):
			QTest.qWait(5)
			if predicate():
				return
		self.fail('Timed out waiting for completion result')

	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])
