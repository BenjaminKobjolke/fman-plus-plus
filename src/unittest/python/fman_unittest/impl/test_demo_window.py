"""Tests for the process helpers used by screenshot demos."""

from unittest import TestCase

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
