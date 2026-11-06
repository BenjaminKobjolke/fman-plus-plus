"""Selection summary listener and settings commands."""
from threading import Thread

from core.selection_summary import (
	FOLDER_SIZES_KEY,
	SUMMARY_LOCATION_KEY,
	SelectionStats,
	SelectionSummaryLocation,
	format_summary,
	get_folder_sizes_enabled,
	get_summary_location,
	measure,
)
from core.settings import save_setting, SETTINGS_FILE
from fman import ApplicationCommand, DirectoryPaneListener, show_status_message


__all__ = [
	'SelectionSummaryListener',
	'ToggleSelectionSummaryLocation',
	'ToggleSelectionFolderSizes',
]


class SelectionSummaryListener(DirectoryPaneListener):
	"""Keep a pane's idle status up to date with its selected entries."""

	def __init__(self, pane):
		super().__init__(pane)
		self._generation = 0
		self._summary_text = ''
		self._refresh()

	def on_selection_changed(self):
		self._refresh()

	def on_path_changed(self):
		self._refresh()

	def on_activated(self):
		self._show_summary(self._summary_text)

	def _refresh(self):
		self._generation += 1
		generation = self._generation
		selected_urls = list(self.pane.get_selected_files())
		stats = measure(selected_urls)
		if get_folder_sizes_enabled() and stats.folder_count:
			self._apply_measurement(
				generation,
				SelectionStats(
					stats.file_count, stats.folder_count,
					stats.size_bytes, calculating=True,
				),
			)
			Thread(
				target=self._measure_folders,
				args=(generation, selected_urls),
				name='selection-summary',
				daemon=True,
			).start()
		else:
			self._apply_measurement(generation, stats)

	def _measure_folders(self, generation, selected_urls):
		stats = measure(
			selected_urls,
			recursive=True,
			is_cancelled=lambda: generation != self._generation,
		)
		self._apply_measurement(generation, stats)

	def _apply_measurement(self, generation, stats):
		if generation != self._generation:
			return
		self._summary_text = format_summary(stats)
		self._show_summary(self._summary_text)

	def _show_summary(self, text):
		location = get_summary_location()
		self.pane.set_idle_status_message(
			text,
			pane_line=location in (
				SelectionSummaryLocation.PANE,
				SelectionSummaryLocation.BOTH,
			),
			status_bar=location in (
				SelectionSummaryLocation.WINDOW,
				SelectionSummaryLocation.BOTH,
			),
		)


def _refresh_panes(window):
	for pane in window.get_panes():
		pane._broadcast('on_selection_changed')


class ToggleSelectionSummaryLocation(ApplicationCommand):
	aliases = ('Toggle selection summary location',)
	_LOCATIONS = (
		SelectionSummaryLocation.PANE,
		SelectionSummaryLocation.WINDOW,
		SelectionSummaryLocation.BOTH,
	)

	def __call__(self):
		current = get_summary_location()
		location = self._LOCATIONS[
			(self._LOCATIONS.index(current) + 1) % len(self._LOCATIONS)
		]
		save_setting(SETTINGS_FILE, SUMMARY_LOCATION_KEY, location.value)
		show_status_message(
			'Selection summary location: ' + location.value,
			timeout_secs=3,
		)
		_refresh_panes(self.window)


class ToggleSelectionFolderSizes(ApplicationCommand):
	aliases = ('Toggle selection folder sizes',)

	def __call__(self):
		enabled = not get_folder_sizes_enabled()
		save_setting(SETTINGS_FILE, FOLDER_SIZES_KEY, enabled)
		state = 'on' if enabled else 'off'
		show_status_message(
			'Selection folder sizes: ' + state,
			timeout_secs=3,
		)
		_refresh_panes(self.window)
