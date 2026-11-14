from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

import guards


class GuardsTest(TestCase):
	def test_is_inside_accepts_file_and_archive_urls(self):
		self.assertTrue(guards.is_inside('file://D:/s/left/x', [r'D:\s']))
		self.assertTrue(guards.is_inside('file:///D:/s/left/x', [r'D:\s']))
		self.assertTrue(guards.is_inside('file://d:/S/LEFT/x', [r'D:\s']))
		self.assertTrue(guards.is_inside(
			'zip://D:/s/left/a.zip/inner', [r'D:\s']))

	def test_is_inside_rejects_sibling_drive_urls_and_missing_path(self):
		for url in (
			'file://D:/DigitalOcean', 'file://D:/s-other', 'drives://', None,
		):
			with self.subTest(url=url):
				self.assertFalse(guards.is_inside(url, [r'D:\s']))

	def test_is_inside_uses_temporary_path_roots(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			child = root / 'left' / 'x'
			self.assertTrue(guards.is_inside(child.as_uri(), [root]))
			self.assertFalse(guards.is_inside(
				(root.parent / 'session-other' / 'x').as_uri(), [root]))

	def test_check_inside_fixtures_reports_first_outside_pane(self):
		with self.assertRaisesRegex(RuntimeError, r'Pane 1.*drives://'):
			guards.check_inside_fixtures({
				'panes': [{'path': 'file://D:/s/left'},
					{'path': 'drives://'}],
			}, [r'D:\s'])

	def test_check_inside_fixtures_rejects_missing_empty_and_malformed_panes(self):
		for state in ({}, {'panes': []}, {'panes': None},
				{'panes': [{}]}, {'panes': [None]}):
			with self.subTest(state=state), self.assertRaises(RuntimeError):
				guards.check_inside_fixtures(state, [r'D:\s'])

	def test_check_no_open_dialog_allows_none_and_progress_dialog(self):
		guards.check_no_open_dialog(None)
		guards.check_no_open_dialog({'type': 'QProgressDialog', 'text': 'Loading'})

	def test_check_no_open_dialog_explains_how_to_answer_prompt(self):
		with self.assertRaisesRegex(
			RuntimeError, r'MessageBox.*Continue\?.*keys Return.*keys Escape'):
			guards.check_no_open_dialog({
				'type': 'MessageBox', 'text': 'Continue?',
			})

	def test_fence_roots_include_profile_parent_and_both_fixtures(self):
		self.assertEqual(
			[Path('/session'), Path('/left'), Path('/right')],
			guards.fence_roots({
				'profile': '/session/profile', 'left': '/left', 'right': '/right',
			}),
		)

	def _session(self, temp):
		root = Path(temp) / 'session'
		left = root / 'left'
		right = root / 'right'
		left.mkdir(parents=True)
		right.mkdir()
		return {'profile': str(root / 'profile'), 'left': str(left),
			'right': str(right)}

	def test_guard_input_fences_every_mutating_action(self):
		with TemporaryDirectory() as temp:
			session = self._session(temp)
			for args in (
				SimpleNamespace(action='keys', chords=['A']),
				SimpleNamespace(action='type', text='hello'),
				SimpleNamespace(action='click', file=None, x=1, y=2),
				SimpleNamespace(action='drag', x=1, y=2, to_x=3, to_y=4),
				SimpleNamespace(action='command', name='new_folder',
					args_json='{}', pane=0),
			):
				with self.subTest(action=args.action):
					api = Mock(return_value={'panes': [
						{'path': 'file://D:/DigitalOcean'},
					]})
					with self.assertRaisesRegex(RuntimeError, 'outside'):
						guards.guard_input(session, args, api)
					self.assertEqual(1, api.call_count)
					self.assertEqual('/v1/state', api.call_args.args[2])

	def test_guard_input_exempts_only_the_single_escape_key(self):
		with TemporaryDirectory() as temp:
			session = self._session(temp)
			api = Mock(return_value={'ok': True})
			self.assertIsNone(guards.guard_input(
				session, SimpleNamespace(action='keys', chords=['Escape']), api))
			api.assert_not_called()

	def test_guard_input_checks_state_for_escape_with_another_key(self):
		with TemporaryDirectory() as temp:
			session = self._session(temp)
			api = Mock(return_value={'panes': [{'path': 'drives://'}]})
			with self.assertRaisesRegex(RuntimeError, 'outside'):
				guards.guard_input(session,
					SimpleNamespace(action='keys', chords=['Escape', 'A']), api)
			api.assert_called_once()

	def test_guard_input_checks_dialog_before_command(self):
		with TemporaryDirectory() as temp:
			session = self._session(temp)
			state = {'panes': [{'path': Path(session['left']).as_uri()}]}
			api = Mock(side_effect=[state, {'dialog': {
				'type': 'MessageBox', 'text': 'Confirm?'}}])
			with self.assertRaisesRegex(RuntimeError, 'Confirm'):
				guards.guard_input(session, SimpleNamespace(action='command'), api)
			self.assertEqual(['/v1/state', '/v1/dialog'],
				[call.args[2] for call in api.call_args_list])

	def test_guard_input_returns_state_for_file_click_and_ignores_read_actions(self):
		with TemporaryDirectory() as temp:
			session = self._session(temp)
			state = {'panes': [{'path': Path(session['left']).as_uri()}]}
			api = Mock(return_value=state)
			self.assertIs(state, guards.guard_input(
				session, SimpleNamespace(action='click'), api))
			api.assert_called_once_with(session, 'GET', '/v1/state')
			for action in ('state', 'files', 'dialog', 'screenshot'):
				with self.subTest(action=action):
					api.reset_mock()
					self.assertIsNone(guards.guard_input(
						session, SimpleNamespace(action=action), api))
					api.assert_not_called()


if __name__ == '__main__':
	from unittest import main
	main()
