from core.commands import pane_size
from core.commands import NarrowActivePane as RegisteredNarrowActivePane, \
	SetPaneSizes as RegisteredSetPaneSizes, \
	WidenActivePane as RegisteredWidenActivePane
from core.commands.pane_size import NarrowActivePane, SetPaneSizes, \
	WidenActivePane, MIN_PANE_PERCENT, preset_sizes, stepped_sizes
from core.tests.commands import FakeWindow
from unittest import TestCase
from unittest.mock import patch


class _FakeWidget:
	def __init__(self, visible=True):
		self.visible = visible
	def isVisible(self):
		return self.visible

class _FakePane:
	def __init__(self, window):
		self.window = window
		self._widget = _FakeWidget()

def _window_with_sizes(sizes):
	window = FakeWindow()
	window.sizes = list(sizes)
	window.get_pane_sizes = lambda: list(window.sizes)
	window.set_pane_sizes = lambda new_sizes: setattr(
		window, 'sizes', list(new_sizes)
	)
	panes = [_FakePane(window) for _ in sizes]
	window._panes = panes
	return window, panes


class PresetSizesTest(TestCase):
	def test_shares_remaining_space_between_other_panes(self):
		self.assertEqual([50, 25, 25], preset_sizes(3, 0, 50))

	def test_equal_preset(self):
		self.assertEqual([100 / 3] * 3, preset_sizes(3, 1, None))

	def test_active_pane_can_be_after_the_first(self):
		self.assertEqual([25, 75], preset_sizes(2, 1, 75))


class SteppedSizesTest(TestCase):
	def test_widen_two_panes(self):
		self.assertEqual([55, 45], stepped_sizes([50, 50], 0, 5))

	def test_widen_splits_space_evenly_between_other_panes(self):
		self.assertEqual([56, 22, 22], stepped_sizes([50, 25, 25], 0, 6))

	def test_narrow_gives_space_evenly_to_other_panes(self):
		self.assertEqual([45, 55], stepped_sizes([50, 50], 0, -5))

	def test_widen_does_not_take_a_pane_below_minimum(self):
		self.assertEqual(
			[100 - MIN_PANE_PERCENT, MIN_PANE_PERCENT],
			stepped_sizes([90, 10], 0, 5)
		)

	def test_narrow_does_not_take_active_pane_below_minimum(self):
		self.assertEqual(
			[MIN_PANE_PERCENT, 100 - MIN_PANE_PERCENT],
			stepped_sizes([12, 88], 0, -5)
		)

	def test_fully_clamped_step_returns_original_sizes(self):
		sizes = [10, 90]
		self.assertIs(sizes, stepped_sizes(sizes, 0, -5))


class PaneSizeCommandsTest(TestCase):
	def test_commands_are_registered(self):
		self.assertIs(RegisteredSetPaneSizes, SetPaneSizes)
		self.assertIs(RegisteredWidenActivePane, WidenActivePane)
		self.assertIs(RegisteredNarrowActivePane, NarrowActivePane)

	def test_set_pane_sizes_forwards_supplied_list(self):
		window, panes = _window_with_sizes([50, 50])
		SetPaneSizes(panes[0])(sizes=[70, 30])
		self.assertEqual([70, 30], window.sizes)

	def test_widen_active_pane_uses_default_step(self):
		window, panes = _window_with_sizes([50, 50])
		WidenActivePane(panes[0])()
		self.assertEqual([55, 45], window.sizes)

	def test_narrow_active_pane_accepts_step(self):
		window, panes = _window_with_sizes([50, 50])
		NarrowActivePane(panes[0])(step=10)
		self.assertEqual([40, 60], window.sizes)

	def test_all_commands_hide_with_one_pane_or_a_hidden_pane(self):
		for command in (SetPaneSizes, WidenActivePane, NarrowActivePane):
			window, panes = _window_with_sizes([100])
			self.assertFalse(command(panes[0]).is_visible())
			window, panes = _window_with_sizes([50, 50])
			panes[1]._widget.visible = False
			self.assertFalse(command(panes[0]).is_visible())

	def test_all_commands_are_visible_for_multiple_shown_panes(self):
		window, panes = _window_with_sizes([50, 50])
		for command in (SetPaneSizes, WidenActivePane, NarrowActivePane):
			self.assertTrue(command(panes[0]).is_visible())

	def test_picker_applies_selected_active_pane_preset(self):
		window, panes = _window_with_sizes([75.5, 24.5])
		with patch.object(pane_size, 'show_quicksearch') as show_quicksearch:
			show_quicksearch.return_value = (0, 75)
			SetPaneSizes(panes[0])()
		self.assertEqual([75, 25], window.sizes)
		current_items = show_quicksearch.call_args.args[0]('')
		current_item = next(item for item in current_items if item.value == 75)
		self.assertEqual('current', current_item.hint)
