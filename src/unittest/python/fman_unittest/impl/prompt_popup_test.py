"""Tests for live completion loading and destination prompts."""

from fman.impl.prompt_suggestions import PromptSuggestions
from fman.impl.prompt_popup import Prompt
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit
from threading import Event, get_ident
from unittest import TestCase


class PromptSuggestionsTest(TestCase):
	@classmethod
	def setUpClass(cls):
		from PyQt5.QtWidgets import QApplication
		cls.app = QApplication.instance() or QApplication([])

	def _wait_for(self, predicate):
		for _ in range(400):
			QTest.qWait(5)
			if predicate():
				return
		self.fail('Timed out waiting for prompt suggestions')

	def test_stale_results_are_discarded(self):
		started, release = Event(), Event()
		results = []
		def complete(text):
			if text == 'old':
				started.set()
				release.wait(2)
			return [text]
		loader = PromptSuggestions(
			complete, lambda text, items: results.append((text, items))
		)
		loader.request('old')
		self._wait_for(started.is_set)
		loader.request('new')
		release.set()
		self._wait_for(lambda: results == [('new', ['new'])])

	def test_callback_error_yields_no_matches(self):
		results = []
		loader = PromptSuggestions(
			lambda _text: (_ for _ in ()).throw(ValueError('bad')),
			lambda text, items: results.append((text, items))
		)
		with self.assertLogs('fman.impl.prompt_suggestions', level='ERROR'):
			loader.request('x')
			self._wait_for(lambda: bool(results))
		self.assertEqual(('x', []), results[0])

	def test_calls_do_not_overlap_and_only_latest_pending_text_runs(self):
		started, release = Event(), Event()
		active, max_active, calls = [0], [0], []
		def complete(text):
			active[0] += 1
			max_active[0] = max(max_active[0], active[0])
			calls.append(text)
			if text == 'first':
				started.set()
				release.wait(2)
			active[0] -= 1
			return [text]
		loader = PromptSuggestions(complete, lambda _text, _items: None)
		loader.request('first')
		self._wait_for(started.is_set)
		loader.request('second')
		loader.request('latest')
		release.set()
		self._wait_for(lambda: calls == ['first', 'latest'])
		self.assertEqual(1, max_active[0])

	def test_close_waits_for_running_completion_then_stops_worker(self):
		started, release = Event(), Event()
		results = []
		def complete(text):
			started.set()
			release.wait(2)
			return [text]
		loader = PromptSuggestions(
			complete, lambda text, items: results.append((text, items))
		)
		loader.request('x')
		self._wait_for(started.is_set)
		loader.close()
		release.set()
		self._wait_for(lambda: not loader._worker.is_alive())
		self.assertEqual([], results)
	def test_results_are_delivered_on_gui_thread(self):
		threads = []
		loader = PromptSuggestions(
			lambda _text: [], lambda _text, _items: threads.append(get_ident())
		)
		loader.request('x')
		self._wait_for(lambda: bool(threads))
		self.assertEqual(get_ident(), threads[0])


class PromptPopupTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])
		cls.css = {
			'border-top-width_px': 0, 'border-bottom-width_px': 1,
			'padding-top_px': 5, 'padding-left_px': 7, 'padding-right_px': 7,
			'title': {'font-size_pts': 11, 'color': QColor('#fff'),
				'highlight': {'color': QColor('#f00')}},
			'hint': {'font-size_pts': 9, 'color': QColor('#aaa')},
			'description': {'font-size_pts': 9, 'color': QColor('#aaa')},
		}

	def setUp(self):
		self.parent = QWidget()
		self.parent.resize(1000, 700)
		self.parent.show()
		self.prompt = Prompt(
			self.parent, _StubApp(), self.css, 'Destination:', 'typed',
			get_completions=lambda text: ['alpha/', 'beta/']
		)
		self.addCleanup(self.prompt.close)

	def test_closing_prompt_stops_suggestion_worker(self):
		worker = self.prompt._suggestions._worker
		self.prompt.reject()
		for _ in range(400):
			QTest.qWait(5)
			if not worker.is_alive():
				break
		self.assertFalse(worker.is_alive())
	def test_message_is_header_and_enter_accepts_exact_field_text(self):
		self.prompt._query.setText('exact destination')
		self.prompt._on_return_pressed()
		self.assertEqual(('exact destination', None), self.prompt.get_result())

	def test_down_selects_a_suggestion_and_updates_text_and_click_does_not_accept(self):
		self.prompt._set_suggestions('typed', ['alpha/', 'beta/'])
		self.prompt._on_key_pressed(_KeyEvent(Qt.Key_Down))
		self.assertEqual('alpha/', self.prompt._query.text())
		self.prompt._set_suggestions('alpha/', ['alpha/', 'beta/'])
		self.prompt._on_item_clicked(self.prompt._items.model().index(1, 0))
		self.assertEqual('beta/', self.prompt._query.text())
		self.assertIsNone(self.prompt.get_result())

	def test_password_and_no_completion_prompt(self):
		password = Prompt(self.parent, _StubApp(), self.css, 'Password', password=True)
		self.assertEqual(QLineEdit.Password, password._query.echoMode())
		self.assertEqual([], password._curr_items)

	def test_base_name_selection_is_applied_after_show_paint(self):
		prompt = Prompt(
			self.parent, _StubApp(), self.css, 'Rename', 'archive.tar.gz',
			selection_start=0, selection_end=7
		)
		prompt.show()
		for _ in range(5):
			QTest.qWait(5)
		self.assertEqual(
			(0, 7), (prompt._query.selectionStart(), len(prompt._query.selectedText()))
		)


class _StubApp:
	def exit(self, _code):
		pass


class _KeyEvent:
	def __init__(self, key):
		self._key = key
	def key(self):
		return self._key
