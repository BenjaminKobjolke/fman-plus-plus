from tempfile import TemporaryDirectory
from unittest import TestCase

from fman.impl.plugins.column_sets import ColumnSets
from fman.impl.util.settings import Settings


class ColumnSetsTest(TestCase):
	def setUp(self):
		self.registered_columns = {
			'core.Name', 'core.Size', 'plugin.GitStatus'
		}
		self.settings_directory = TemporaryDirectory()
		self.addCleanup(self.settings_directory.cleanup)
		self.settings_path = self.settings_directory.name + '/Column Settings.json'
		self.settings = Settings(self.settings_path)
		self.column_sets = ColumnSets(
			self.settings, lambda: self.registered_columns
		)

	def test_lookup_prefers_folder_then_scheme_then_filesystem_defaults(self):
		defaults = ('core.Name', 'core.Size')
		self.assertEqual(defaults, self.column_sets.get_columns('file://a', defaults))
		self.column_sets.set_default_columns('file://', ('core.Name',))
		self.assertEqual(
			('core.Name',), self.column_sets.get_columns('file://a', defaults)
		)
		self.column_sets.set_columns('file://a', ('core.Name', 'plugin.GitStatus'))
		self.assertEqual(
			('core.Name', 'plugin.GitStatus'),
			self.column_sets.get_columns('file://a', defaults)
		)
		self.assertEqual(
			('core.Name',), self.column_sets.get_columns('file://b', defaults)
		)

	def test_reset_reveals_next_override_layer(self):
		defaults = ('core.Name', 'core.Size')
		self.column_sets.set_default_columns('file://', ('core.Name',))
		self.column_sets.set_columns('file://a', ('core.Name', 'plugin.GitStatus'))
		self.column_sets.reset_columns('file://a')
		self.assertEqual(
			('core.Name',), self.column_sets.get_columns('file://a', defaults)
		)
		self.column_sets.reset_default_columns('file://')
		self.assertEqual(defaults, self.column_sets.get_columns('file://a', defaults))

	def test_setters_reject_unregistered_columns(self):
		with self.assertRaisesRegex(ValueError, 'plugin.Missing'):
			self.column_sets.set_default_columns('file://', ('plugin.Missing',))
		with self.assertRaisesRegex(ValueError, 'plugin.Missing'):
			self.column_sets.set_columns('file://a', ('core.Name', 'plugin.Missing'))

	def test_saved_unknown_columns_are_filtered_and_empty_set_falls_back(self):
		self.settings['file://a'] = ['core.Name', 'plugin.Removed']
		self.settings['file://b'] = ['plugin.Removed']
		self.settings.flush()
		column_sets = ColumnSets(
			Settings(self.settings_path), lambda: self.registered_columns
		)
		self.assertEqual(
			('core.Name',),
			column_sets.get_columns('file://a', ('core.Name', 'core.Size'))
		)
		self.assertEqual(
			('core.Name', 'core.Size'),
			column_sets.get_columns('file://b', ('core.Name', 'core.Size'))
		)

	def test_changes_emit_the_affected_scheme_or_folder(self):
		changes = []
		self.column_sets.changed.add_callback(changes.append)
		self.column_sets.set_default_columns('file://', ('core.Name',))
		self.column_sets.set_columns('file://a', ('core.Name', 'core.Size'))
		self.column_sets.reset_columns('file://a')
		self.column_sets.reset_default_columns('file://')
		self.assertEqual(['file://', 'file://a', 'file://a', 'file://'], changes)

	def test_folder_set_round_trips_and_reset_removes_saved_key(self):
		self.column_sets.set_columns('file://a', ('core.Name', 'plugin.GitStatus'))
		reloaded = ColumnSets(
			Settings(self.settings_path), lambda: self.registered_columns
		)
		self.assertEqual(
			('core.Name', 'plugin.GitStatus'),
			reloaded.get_columns('file://a', ('core.Name', 'core.Size'))
		)
		reloaded.reset_columns('file://a')
		self.assertIsNone(Settings(self.settings_path).get('file://a', None))
