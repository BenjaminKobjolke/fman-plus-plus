import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import fman_ui


class FmanUiActionTest(TestCase):
	def _write_session(self, temp):
		root = Path(temp) / 'fman-ui'
		left = root / 'left'
		right = root / 'right'
		left.mkdir(parents=True)
		right.mkdir()
		session = {
			'session_id': 'x', 'pid': 1, 'port': 1,
			'token_path': str(root / 'profile' / 'token'),
			'profile': str(root / 'profile'),
			'left': str(left), 'right': str(right),
		}
		Path(session['token_path']).parent.mkdir(parents=True)
		Path(session['token_path']).write_text('token')
		(root / 'current.json').write_text(json.dumps(session))
		return session

	def test_bare_file_name_is_resolved_against_selected_pane(self):
		with TemporaryDirectory() as temp:
			self._write_session(temp)
			with patch.dict(os.environ, {'TEMP': temp}), \
				patch.object(fman_ui, '_api', side_effect=[
					{'panes': [{'path': Path(temp, 'fman-ui', 'left').as_uri()}]},
					{'ok': True},
				]) as api:
				self.assertEqual(0, fman_ui.main([
					'click', '--file', 'visible.txt', '--settle', '0']))
				self.assertEqual(
					Path(temp, 'fman-ui', 'left').as_uri() + '/visible.txt',
					api.call_args_list[1].args[3]['file'],
				)

	def test_drag_posts_start_and_end_coordinates(self):
		with TemporaryDirectory() as temp:
			self._write_session(temp)
			with patch.dict(os.environ, {'TEMP': temp}), \
				patch.object(fman_ui, '_api', side_effect=[
					{'panes': [{'path': Path(temp, 'fman-ui', 'left').as_uri()}]},
					{'ok': True},
				]) as api:
				self.assertEqual(0, fman_ui.main([
					'drag', '--x', '1', '--y', '2', '--to-x', '3', '--to-y', '4',
					'--settle', '0',
				]))
		self.assertEqual(
			('POST', '/v1/drag', {'x': 1, 'y': 2, 'to_x': 3, 'to_y': 4}),
			api.call_args.args[1:],
		)

	def test_drop_posts_session_files_and_selected_action(self):
		with TemporaryDirectory() as temp:
			session = self._write_session(temp)
			session_root = Path(session['profile']).parent
			source = session_root / 'drop_source' / 'dropped.txt'
			source.parent.mkdir()
			source.write_text('drop fixture\n', encoding='utf-8')
			state = {'panes': [
				{'path': Path(session['left']).as_uri()},
				{'path': Path(session['right']).as_uri()},
			]}
			for option, action in (('--copy', 'copy'), ('--move', 'move')):
				with self.subTest(action=action), \
					patch.dict(os.environ, {'TEMP': temp}), \
					patch.object(fman_ui, '_read_current', return_value=session), \
					patch.object(fman_ui, '_api', side_effect=[
						state, {'ok': True},
					]) as api:
					self.assertEqual(0, fman_ui.main([
						'drop', '--file', str(source), '--pane', '1',
						'--onto', 'folder', option, '--settle', '0',
					]))
				self.assertEqual(
					('POST', '/v1/drop', {
						'pane': 1,
						'files': [str(source.resolve())],
						'onto': 'folder',
						'action': action,
					}),
					api.call_args_list[1].args[1:],
				)

	def test_bracketed_and_spaced_file_names_remain_unencoded(self):
		with TemporaryDirectory() as temp:
			self._write_session(temp)
			for name in ('[--brackets--]/visible.txt', 'file name.txt'):
				with self.subTest(name=name), \
					patch.dict(os.environ, {'TEMP': temp}), \
					patch.object(fman_ui, '_api', side_effect=[
						{'panes': [{
							'path': Path(temp, 'fman-ui', 'left').as_uri(),
						}]},
						{'ok': True},
					]) as api:
					self.assertEqual(0, fman_ui.main([
						'click', '--file', name, '--settle', '0']))
				self.assertEqual(
					Path(temp, 'fman-ui', 'left').as_uri() + '/' + name,
					api.call_args_list[1].args[3]['file'],
				)

	def test_drag_file_resolves_source_and_target_names_and_selected_action(self):
		with TemporaryDirectory() as temp:
			session = self._write_session(temp)
			state = {'panes': [
				{'path': Path(session['left']).as_uri()},
				{'path': Path(session['right']).as_uri()},
			]}
			for option, action in (
				('--copy', 'copy'), ('--move', 'move'), (None, 'default'),
			):
				with self.subTest(action=action), \
					patch.dict(os.environ, {'TEMP': temp}), \
					patch.object(fman_ui, '_read_current', return_value=session), \
					patch.object(fman_ui, '_api', side_effect=[
						state, {'ok': True},
					]) as api:
					self.assertEqual(0, fman_ui.main([
						'drag-file', '--file', '[--brackets--]/visible.txt',
						'--pane', '0', '--to-pane', '1', '--onto', 'folder',
						*([option] if option else []), '--settle', '0',
					]))
				self.assertEqual(('POST', '/v1/drag-files', {
					'source_pane': 0,
					'files': [Path(session['left']).as_uri() +
						'/[--brackets--]/visible.txt'],
					'pane': 1,
					'onto': Path(session['right']).as_uri() + '/folder',
					'action': action,
				}), api.call_args_list[1].args[1:])

	def test_drag_file_rejects_pane_index_outside_state(self):
		with TemporaryDirectory() as temp:
			session = self._write_session(temp)
			state = {'panes': [
				{'path': Path(session['left']).as_uri()},
			]}
			with patch.dict(os.environ, {'TEMP': temp}), \
				patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_api', return_value=state) as api:
				self.assertEqual(1, fman_ui.main([
					'drag-file', '--file', 'visible.txt', '--pane', '0',
					'--to-pane', '1', '--settle', '0',
				]))
			api.assert_called_once_with(session, 'GET', '/v1/state')


if __name__ == '__main__':
	from unittest import main

	main()
