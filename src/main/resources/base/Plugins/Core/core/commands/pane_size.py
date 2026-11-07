"""Set pane widths for upstream #387 using pane indexes in window order.

The public Window API accepts a whole list of relative sizes, so the commands
work with any pane count and leave pixel conversion to fman's window layer.
"""
from core.commands.pane_view import _any_pane_hidden
from core.commands.theme import _matched_items
from fman import DirectoryPaneCommand, show_quicksearch
from typing import Sequence

__all__ = ['NarrowActivePane', 'SetPaneSizes', 'WidenActivePane']

PRESET_SHARES = (25, 33, 67, 75)
EQUAL_LABEL = 'Equal'
DEFAULT_STEP_PERCENT = 5
MIN_PANE_PERCENT = 10


def preset_sizes(
	pane_count: int, active_index: int, share: float | None
) -> list[float]:
	if share is None:
		return [100 / pane_count] * pane_count
	other_share = (100 - share) / (pane_count - 1)
	return [
		share if index == active_index else other_share
		for index in range(pane_count)
	]


def stepped_sizes(
	sizes: Sequence[float], active_index: int, delta: float
) -> Sequence[float]:
	"""Move the active pane by delta points, sharing space with its siblings."""
	if not delta:
		return sizes
	others = [index for index in range(len(sizes)) if index != active_index]
	if delta > 0:
		available = sum(
			max(0, sizes[index] - MIN_PANE_PERCENT) for index in others
		)
		amount = min(delta, available)
		if amount == 0:
			return sizes
		result = list(sizes)
		remaining = amount
		eligible = [index for index in others if result[index] > MIN_PANE_PERCENT]
		while eligible and remaining > 0:
			share = remaining / len(eligible)
			next_eligible = []
			for index in eligible:
				can_give = result[index] - MIN_PANE_PERCENT
				given = min(share, can_give)
				result[index] -= given
				remaining -= given
				if can_give > share:
					next_eligible.append(index)
			eligible = next_eligible
		result[active_index] += amount
	else:
		amount = min(-delta, max(0, sizes[active_index] - MIN_PANE_PERCENT))
		if amount == 0:
			return sizes
		result = list(sizes)
		result[active_index] -= amount
		for index in others:
			result[index] += amount / len(others)
	return result


def _can_set_pane_sizes(panes: Sequence[object]) -> bool:
	return len(panes) > 1 and not _any_pane_hidden(panes)


def _preset_entries() -> list[tuple[int | None, str]]:
	return [(None, EQUAL_LABEL)] + [
		(share, 'Active pane %d%%' % share) for share in PRESET_SHARES
	]


def _current_preset(sizes: Sequence[float], active_index: int) -> object:
	equal_share = 100 / len(sizes)
	if all(abs(size - equal_share) <= 1 for size in sizes):
		return None
	active_share = sizes[active_index]
	return next((
		share for share in PRESET_SHARES
		if abs(active_share - share) <= 1
	), object())


class SetPaneSizes(DirectoryPaneCommand):
	aliases = ('Set pane sizes',)
	usable_in_viewer = True

	def is_visible(self) -> bool:
		return _can_set_pane_sizes(self.pane.window.get_panes())

	def __call__(self, sizes: Sequence[float] | None = None) -> None:
		window = self.pane.window
		if sizes is not None:
			window.set_pane_sizes(sizes)
			return
		panes = window.get_panes()
		active_index = panes.index(self.pane)
		entries = _preset_entries()
		current = _current_preset(window.get_pane_sizes(), active_index)

		def apply_value(share: int | None) -> None:
			window.set_pane_sizes(
				preset_sizes(len(panes), active_index, share)
			)

		values = [value for value, _ in entries]
		item = values.index(current) if current in values else 0
		result = show_quicksearch(
			lambda query: _matched_items(entries, current, query), item=item
		)
		if result:
			apply_value(result[1])


class _StepActivePane(DirectoryPaneCommand):
	usable_in_viewer = True

	def is_visible(self) -> bool:
		return _can_set_pane_sizes(self.pane.window.get_panes())

	def __call__(self, step: float = DEFAULT_STEP_PERCENT) -> None:
		window = self.pane.window
		panes = window.get_panes()
		if not _can_set_pane_sizes(panes):
			return
		window.set_pane_sizes(stepped_sizes(
			window.get_pane_sizes(), panes.index(self.pane), self._direction * step
		))


class WidenActivePane(_StepActivePane):
	aliases = ('Widen active pane',)
	_direction = 1


class NarrowActivePane(_StepActivePane):
	aliases = ('Narrow active pane',)
	_direction = -1
