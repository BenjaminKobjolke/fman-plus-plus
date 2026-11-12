from core.tests.viewer_stubs import FakeSettings
from core.videoviewer import (
	VIDEO_EXTENSIONS, PaneVideoView, VideoPlaybackState, format_time,
	get_saved_mute, get_saved_volume, is_video, save_mute, save_volume,
	show_video_viewer,
)
from unittest import TestCase
from unittest.mock import patch

import sys
from types import SimpleNamespace


class PlaybackStateTest(TestCase):
	def test_empty_before_player_is_created(self):
		view = SimpleNamespace(_player=None)
		self.assertEqual(
			VideoPlaybackState(False, None, None, None),
			PaneVideoView.playback_state(view),
		)

	def test_reads_pause_position_and_duration_from_player(self):
		player = SimpleNamespace(
			pause=False, time_pos=12.5, duration=30.0,
		)
		view = SimpleNamespace(_player=player)
		self.assertEqual(
			VideoPlaybackState(True, False, 12.5, 30.0),
			PaneVideoView.playback_state(view),
		)

class IsVideoTest(TestCase):
	def test_matches_every_known_video_extension(self):
		for ext in VIDEO_EXTENSIONS:
			self.assertTrue(is_video('file:///a/b/c%s' % ext))

	def test_case_insensitive(self):
		self.assertTrue(is_video('file:///a/b/c.MP4'))

	def test_non_video_extension_is_rejected(self):
		self.assertFalse(is_video('file:///a/b/c.txt'))

	def test_no_extension_is_rejected(self):
		self.assertFalse(is_video('file:///a/b/c'))

class FormatTimeTest(TestCase):
	def test_zero(self):
		self.assertEqual('0:00', format_time(0))

	def test_none_is_zero(self):
		self.assertEqual('0:00', format_time(None))

	def test_negative_is_zero(self):
		self.assertEqual('0:00', format_time(-5))

	def test_minutes_and_seconds(self):
		self.assertEqual('1:12', format_time(72))

	def test_hours_minutes_and_seconds(self):
		self.assertEqual('1:01:01', format_time(3661))

class VolumeAndMutePersistenceTest(TestCase):
	def setUp(self):
		self._settings = FakeSettings()
		patcher_get = patch('core.videoviewer.get_setting', self._settings.get)
		patcher_save = patch('core.videoviewer.save_setting', self._settings.save)
		patcher_get.start()
		patcher_save.start()
		self.addCleanup(patcher_get.stop)
		self.addCleanup(patcher_save.stop)

	def test_volume_round_trips(self):
		save_volume(50)
		self.assertEqual(50, get_saved_volume())

	def test_volume_defaults_to_none_when_nothing_saved(self):
		self.assertIsNone(get_saved_volume())

	def test_mute_defaults_to_false_when_nothing_saved(self):
		self.assertIs(False, get_saved_mute())

	def test_mute_round_trips_true(self):
		save_mute(True)
		self.assertIs(True, get_saved_mute())

class ShowVideoViewerTest(TestCase):
	def test_missing_mpv_module_shows_alert(self):
		# sys.modules[name] = None makes `import name` raise ImportError. That
		# reproduces the frozen build, where the Core plugin ships as resource
		# data so PyInstaller never sees `import mpv` (see the mpv entry in
		# src/build/settings/base.json's hidden_imports).
		with patch.dict(sys.modules, {'mpv': None}), \
				patch('core.videoviewer.ensure_libmpv_on_path'), \
				patch('core.videoviewer.show_alert') as alert, \
				patch('core.videoviewer._open_video_view') as open_view:
			show_video_viewer(None, 'file:///a/b/c.mp4')
		self.assertEqual(1, alert.call_count)
		open_view.assert_not_called()
