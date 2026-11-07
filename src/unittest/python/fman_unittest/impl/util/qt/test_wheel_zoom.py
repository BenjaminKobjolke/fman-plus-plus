from fman.impl.util.qt.wheel_zoom import CtrlWheelZoom
from PyQt5.QtCore import Qt
from unittest import TestCase


class CtrlWheelZoomTest(TestCase):

	def setUp(self):
		self.steps = []
		self.zoom = CtrlWheelZoom(self.steps.append)

	def test_does_not_consume_wheel_without_control(self):
		self.assertFalse(self.zoom.handle(_WheelEvent(120, Qt.NoModifier)))
		self.assertEqual([], self.steps)

	def test_emits_a_step_for_each_positive_notch(self):
		self.assertTrue(self.zoom.handle(_WheelEvent(240, Qt.ControlModifier)))
		self.assertEqual([1, 1], self.steps)

	def test_emits_a_negative_step_for_each_negative_notch(self):
		self.assertTrue(self.zoom.handle(_WheelEvent(-240, Qt.ControlModifier)))
		self.assertEqual([-1, -1], self.steps)

	def test_accumulates_touchpad_deltas_until_a_notch(self):
		self.zoom.handle(_WheelEvent(40, Qt.ControlModifier))
		self.zoom.handle(_WheelEvent(40, Qt.ControlModifier))
		self.assertEqual([], self.steps)
		self.zoom.handle(_WheelEvent(40, Qt.ControlModifier))
		self.assertEqual([1], self.steps)

	def test_opposite_deltas_cancel_the_signed_remainder(self):
		self.zoom.handle(_WheelEvent(80, Qt.ControlModifier))
		self.zoom.handle(_WheelEvent(-80, Qt.ControlModifier))
		self.zoom.handle(_WheelEvent(40, Qt.ControlModifier))
		self.assertEqual([], self.steps)
		self.zoom.handle(_WheelEvent(80, Qt.ControlModifier))
		self.assertEqual([1], self.steps)

	def test_remainder_is_reset_when_control_is_released(self):
		self.zoom.handle(_WheelEvent(80, Qt.ControlModifier))
		self.zoom.handle(_WheelEvent(0, Qt.NoModifier))
		self.zoom.handle(_WheelEvent(40, Qt.ControlModifier))
		self.assertEqual([], self.steps)

	def test_does_not_consume_horizontal_only_wheel_input(self):
		self.assertFalse(self.zoom.handle(_WheelEvent(0, Qt.ControlModifier)))
		self.assertEqual([], self.steps)


class _WheelDelta:
	def __init__(self, y):
		self._y = y
	def y(self):
		return self._y


class _WheelEvent:
	def __init__(self, delta_y, modifiers):
		self._delta_y = delta_y
		self._modifiers = modifiers
	def angleDelta(self):
		return _WheelDelta(self._delta_y)
	def modifiers(self):
		return self._modifiers
