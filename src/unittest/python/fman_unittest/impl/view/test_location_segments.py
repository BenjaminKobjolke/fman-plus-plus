from fman.url import as_human_readable
from fman.impl.view.location_segments import (
	LocationSegment, child_on_path, location_segments, segment_at
)
from unittest import TestCase


class LocationSegmentsTest(TestCase):
	def test_windows_file_url_segments_end_at_parent_names(self):
		url = 'file://C:/Users/Michael/dev/fman'
		segments = location_segments(url)

		self.assertEqual(
			[
				LocationSegment('file://C:', len(as_human_readable('file://C:'))),
				LocationSegment('file://C:/Users', len(as_human_readable('file://C:/Users'))),
				LocationSegment(
					'file://C:/Users/Michael',
					len(as_human_readable('file://C:/Users/Michael'))
				),
				LocationSegment(
					'file://C:/Users/Michael/dev',
					len(as_human_readable('file://C:/Users/Michael/dev'))
				),
			],
			segments
		)

	def test_unix_file_url_segments_end_at_parent_names(self):
		url = 'file:///home/michael/dev/fman'
		segments = location_segments(url)

		self.assertEqual(
			[
				LocationSegment('file:///', 1),
				LocationSegment('file:///home', len('/home')),
				LocationSegment('file:///home/michael', len('/home/michael')),
				LocationSegment('file:///home/michael/dev', len('/home/michael/dev')),
			],
			segments
		)

	def test_zip_url_keeps_archive_scheme_in_parent_segments(self):
		url = 'zip://C:/archive.zip/folder/current'
		segments = location_segments(url)

		self.assertEqual(
			[
				LocationSegment('zip://C:', len('zip://C:')),
				LocationSegment('zip://C:/archive.zip', len('zip://C:/archive.zip')),
				LocationSegment(
					'zip://C:/archive.zip/folder',
					len('zip://C:/archive.zip/folder')
				),
			],
			segments
		)

	def test_root_urls_have_no_clickable_parent_segments(self):
		self.assertEqual([], location_segments('file:///'))
		self.assertEqual([], location_segments('zip://'))

	def test_segment_at_uses_character_positions_before_segment_end(self):
		segments = [
			LocationSegment('file:///home', 5),
			LocationSegment('file:///home/me', 8)
		]

		self.assertEqual(segments[0], segment_at(segments, 0))
		self.assertEqual(segments[0], segment_at(segments, 4))
		self.assertEqual(segments[1], segment_at(segments, 5))
		self.assertIsNone(segment_at(segments, 8))

	def test_child_on_path_returns_immediate_child_below_parent(self):
		self.assertEqual(
			'file:///home/michael',
			child_on_path('file:///home', 'file:///home/michael/dev/fman')
		)

	def test_child_on_path_rejects_unrelated_urls(self):
		self.assertIsNone(child_on_path('file:///home/michael', 'file:///home/mike/dev'))
		self.assertIsNone(child_on_path('file:///home', 'zip:///home/michael/dev'))
