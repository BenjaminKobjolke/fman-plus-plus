"""Demo 32 only: provides a plugin-owned column and toggle command."""

from fman import DirectoryPaneCommand, DirectoryPaneListener
from fman.fs import Column, set_default_columns


class Tag(Column):
	def get_str(self, url):
		return 'plugin'

	def get_widest_str(self):
		return 'plugin'


class ShowDemoTagColumn(DirectoryPaneListener):
	_columns_set = False

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if not self._columns_set:
			set_default_columns(
				'file://',
				(
					'core.Name',
					'core.file_columns.Extension',
					'core.Size',
					'core.Modified',
					Tag.get_qualified_name(),
				),
			)
			self.__class__._columns_set = True


class ToggleDemoTagColumn(DirectoryPaneCommand):
	aliases = ('Toggle demo tag column',)

	def __call__(self):
		self.pane.run_command(
			'toggle_column', {'column': Tag.get_qualified_name()}
		)
