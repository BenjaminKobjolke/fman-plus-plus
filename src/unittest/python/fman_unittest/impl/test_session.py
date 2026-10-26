from fman.impl import incognito
from fman.impl.session import SessionManager
from unittest import TestCase


class SessionManagerCloseTest(TestCase):
	def setUp(self):
		self.addCleanup(incognito.set_incognito, False)
		self.settings = _Settings({
			'panes': [{'location': 'file://C:/before', 'col_widths': [100]}]
		})
		self.manager = SessionManager(self.settings, None, None, '1.2.3')
		self.window = _MainWindow([_Pane('file://C:/after', [200])])

	def test_saves_panes_when_not_incognito(self):
		incognito.set_incognito(False)

		self.manager.on_close(self.window)

		self.assertEqual(
			[{'location': 'file://C:/after', 'col_widths': [200]}],
			self.settings['panes'])
		self._assert_window_settings_saved()

	def test_saves_remembered_panes_but_current_column_widths_when_incognito(self):
		incognito.remember_pane_states([
			incognito.PaneState('file://C:/snapshot', 'file://C:/snapshot/file.txt')
		])
		incognito.set_incognito(True)

		self.manager.on_close(self.window)

		self.assertEqual(
			[{'location': 'file://C:/snapshot', 'col_widths': [200]}],
			self.settings['panes'])
		self._assert_window_settings_saved()

	def test_preserves_previous_panes_when_incognito_has_no_snapshot(self):
		previous_panes = self.settings['panes']
		incognito.set_incognito(True)

		self.manager.on_close(self.window)

		self.assertIs(previous_panes, self.settings['panes'])
		self._assert_window_settings_saved()

	def _assert_window_settings_saved(self):
		self.assertEqual('Z2VvbWV0cnk=', self.settings['window_geometry'])
		self.assertEqual('c3RhdGU=', self.settings['window_state'])
		self.assertEqual('1.2.3', self.settings['fman_version'])
		self.assertEqual(1, self.settings.flush_count)


class _Settings(dict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.flush_count = 0
	def flush(self):
		self.flush_count += 1


class _MainWindow:
	def __init__(self, panes):
		self._panes = panes
	def saveGeometry(self):
		return b'geometry'
	def saveState(self, version):
		return b'state'
	def get_panes(self):
		return self._panes


class _Pane:
	def __init__(self, location, col_widths):
		self._location = location
		self._col_widths = col_widths
	def get_location(self):
		return self._location
	def get_column_widths(self):
		return self._col_widths
