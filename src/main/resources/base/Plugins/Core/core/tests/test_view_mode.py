from core.commands.view_mode import ToggleCompactView
from unittest import TestCase
from unittest.mock import Mock


class ToggleCompactViewTest(TestCase):
	def test_toggles_the_active_panes_view_mode(self):
		pane = Mock()
		pane._widget.is_compact_view.return_value = False

		ToggleCompactView(pane)()

		pane._widget.set_compact_view.assert_called_once_with(True)
