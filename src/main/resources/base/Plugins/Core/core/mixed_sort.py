"""Shared sorting behavior for Core columns when panes mix files and folders.

The per-pane switch is managed by core.commands.mixed_sorting.
"""


class DirsFirstColumn:
	def get_mixed_sort_value(self, url, is_ascending):
		return self.get_sort_value(url, is_ascending)[1:]
