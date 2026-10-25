from core.imageviewer_zoom import (
	MAX_SCALE, MIN_SCALE, change_image_scale, clamp_scale, reset_image_scale,
	zoom_message,
)
from unittest import TestCase

class _FakeView:
	# Stands in for PaneImageView.effective_scale() - the "what's actually
	# on screen right now" fallback used when nothing is saved yet.
	def effective_scale(self):
		return 1.0
	def __init__(self):
		from core.tests.viewer_stubs import StubPane
		self._nav = type('Nav', (), {'pane': StubPane([])})()

class ClampScaleTest(TestCase):
	def test_clamps_below_minimum(self):
		self.assertEqual(MIN_SCALE, clamp_scale(0.01))

	def test_clamps_above_maximum(self):
		self.assertEqual(MAX_SCALE, clamp_scale(100))

	def test_leaves_in_range_value_untouched(self):
		self.assertEqual(2.0, clamp_scale(2.0))

class ZoomMessageTest(TestCase):
	# The one formatter PaneImageView._actual_size reuses, so "Actual size"
	# and a zoom step that lands on 1.0 can't drift apart.
	def test_reports_a_scale_as_a_percentage(self):
		self.assertEqual('Zoom 100%', zoom_message(1.0))

	def test_rounds_to_whole_percent(self):
		self.assertEqual('Zoom 125%', zoom_message(1.25))

class ChangeImageScaleTest(TestCase):
	def test_steps_up_from_saved_scale(self):
		result = {}
		change_image_scale(
			_FakeView(), lambda s: result.setdefault('applied', s), +1,
			get_saved=lambda: 1.0, save=lambda s: result.setdefault('saved', s),
		)
		self.assertAlmostEqual(1.25, result['applied'])
		self.assertAlmostEqual(1.25, result['saved'])

	def test_steps_down_from_saved_scale(self):
		result = {}
		change_image_scale(
			_FakeView(), lambda s: result.setdefault('applied', s), -1,
			get_saved=lambda: 1.25, save=lambda s: None,
		)
		self.assertAlmostEqual(1.0, result['applied'])

	def test_falls_back_to_view_effective_scale_when_nothing_saved(self):
		# Nothing saved (fit mode) - must step from the view's current
		# effective scale, not a hardcoded 1.0.
		result = {}
		change_image_scale(
			_FakeView(), lambda s: result.setdefault('applied', s), +1,
			get_saved=lambda: None, save=lambda s: None,
		)
		self.assertAlmostEqual(1.25, result['applied'])

	def test_clamps_to_maximum(self):
		result = {}
		change_image_scale(
			_FakeView(), lambda s: result.setdefault('applied', s), +1,
			get_saved=lambda: MAX_SCALE, save=lambda s: None,
		)
		self.assertEqual(MAX_SCALE, result['applied'])

class ResetImageScaleTest(TestCase):
	def test_clears_saved_scale_and_applies_fit_mode(self):
		result = {}
		view = _FakeView()
		reset_image_scale(
			view,
			lambda s: result.setdefault('applied', s),
			save=lambda s: result.setdefault('saved', s),
		)
		self.assertIsNone(result['saved'])
		self.assertIsNone(result['applied'])
		self.assertEqual([('Fit to window', 3)], view._nav.pane.status_messages)
