"""Demo-only file drop action used by the screenshot recorder."""

from dataclasses import dataclass

from fman.impl.plugins import PluginSupport


@dataclass(frozen=True)
class DropCursorFile:
	"""Drop the active pane's file under the cursor onto the opposite pane \
	as a mouse drop would."""

	copy: bool = True


def drop_cursor_file(
	plugin_support: PluginSupport, step: DropCursorFile
) -> None:
	active = plugin_support.get_active_pane()
	file_url = active.get_file_under_cursor()
	if file_url is None:
		raise ValueError('There is no file under the cursor to drop.')
	other = next(
		pane for pane in plugin_support.get_panes() if pane is not active
	)
	active._widget._on_files_dropped(
		[file_url], other.get_path(), step.copy
	)
