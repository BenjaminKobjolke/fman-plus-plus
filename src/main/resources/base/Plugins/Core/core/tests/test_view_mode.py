from core.commands.view_mode import (
	InitThumbnailView, ToggleCompactView, ToggleThumbnailView,
)
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock, patch

_APP = QApplication.instance() or QApplication([])


class ToggleCompactViewTest(TestCase):
	def test_toggles_the_active_panes_view_mode(self):
		pane = Mock()
		pane._widget.is_compact_view.return_value = False

		ToggleCompactView(pane)()

		pane._widget.set_compact_view.assert_called_once_with(True)


class ToggleThumbnailViewTest(TestCase):
	def test_enabling_applies_current_settings_before_switching(self):
		pane = Mock()
		pane._widget.is_thumbnail_view.return_value = False
		settings = Mock()
		with patch('core.commands.view_mode.get_thumbnail_settings',
				   return_value=settings):
			ToggleThumbnailView(pane)()

		pane._widget.set_thumbnail_settings.assert_called_once_with(settings)
		pane._widget.set_thumbnail_view.assert_called_once_with(True)

	def test_disabling_does_not_reload_settings(self):
		pane = Mock()
		pane._widget.is_thumbnail_view.return_value = True
		with patch('core.commands.view_mode.get_thumbnail_settings') as settings:
			ToggleThumbnailView(pane)()

		settings.assert_not_called()
		pane._widget.set_thumbnail_view.assert_called_once_with(False)


class InitThumbnailViewTest(TestCase):
	def test_applies_current_settings_when_pane_is_created(self):
		pane = Mock()
		settings = Mock()
		with patch('core.commands.view_mode.get_thumbnail_settings',
				   return_value=settings):
			InitThumbnailView(pane)

		pane._widget.set_thumbnail_settings.assert_called_once_with(settings)
