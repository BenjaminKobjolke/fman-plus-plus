"""Demo 34 only: sets up six columns for narrow-pane screenshots."""

from fman import DirectoryPaneListener
from fman.fs import Column, set_default_columns


class FixedTextColumn(Column):
	value: str

	def get_str(self, url: str) -> str:
		return self.value

	def get_widest_str(self) -> str:
		return self.value


class Permissions(FixedTextColumn):
	value = 'rw-r--r--'


class Owner(FixedTextColumn):
	value = 'demo-owner'


class Group(FixedTextColumn):
	value = 'demo-group'


class SetNarrowColumns(DirectoryPaneListener):
	_columns_set = False

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if not self._columns_set:
			set_default_columns(
				'file://',
				(
					'core.Name',
					'core.Size',
					'core.Modified',
					Permissions.get_qualified_name(),
					Owner.get_qualified_name(),
					Group.get_qualified_name(),
				),
			)
			self.__class__._columns_set = True
