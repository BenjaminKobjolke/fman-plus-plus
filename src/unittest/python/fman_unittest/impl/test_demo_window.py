"""Tests for the process helpers used by screenshot demos."""

import sys
from unittest import TestCase, skipUnless
from unittest.mock import patch

from fman.impl import demo_window
from fman.impl.demo_window import process_tree


class ProcessTreeTest(TestCase):
	def test_process_tree_includes_only_the_root(self):
		self.assertEqual({10}, process_tree(10, {}))

	def test_process_tree_includes_a_child(self):
		self.assertEqual({10, 11}, process_tree(10, {11: 10}))

	def test_process_tree_includes_a_grandchild(self):
		self.assertEqual(
			{10, 11, 12}, process_tree(10, {11: 10, 12: 11}),
		)

	def test_process_tree_excludes_unrelated_processes(self):
		self.assertEqual(
			{10, 11}, process_tree(10, {11: 10, 20: 19}),
		)

	def test_process_tree_ends_when_the_parent_map_has_a_cycle(self):
		self.assertEqual(
			{10, 11, 12}, process_tree(10, {11: 10, 12: 11, 10: 12}),
		)


@skipUnless(sys.platform == 'win32', 'Windows window APIs are required')
class ForegroundProcessWindowTest(TestCase):
	@patch.object(demo_window, '_bring_to_foreground', return_value=False)
	@patch.object(demo_window, '_find_process_window', return_value=456)
	def test_returns_window_when_it_cannot_be_brought_to_foreground(
		self, find_window, bring_to_foreground,
	):
		self.assertEqual(456, demo_window.foreground_process_window(123, 'x'))
		find_window.assert_called_once_with(123, 'x')
		bring_to_foreground.assert_called_once_with(123, 456)

	@patch.object(demo_window, '_bring_to_foreground')
	@patch.object(demo_window, '_find_process_window', return_value=None)
	def test_returns_none_when_no_window_is_found(
		self, find_window, bring_to_foreground,
	):
		self.assertIsNone(demo_window.foreground_process_window(123, 'x'))
		find_window.assert_called_once_with(123, 'x')
		bring_to_foreground.assert_not_called()
