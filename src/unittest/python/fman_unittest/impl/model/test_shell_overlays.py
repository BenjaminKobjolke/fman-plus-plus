from fman.impl.model.shell_overlays import ShellOverlays, _decode_overlay_index
from threading import Lock, local
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
import sys


class ShellOverlaysTest(TestCase):

	def test_initializes_windows_image_list_apis(self):
		overlays = ShellOverlays()

		self.assertIsNotNone(overlays._comctl32.HIMAGELIST_QueryInterface)

	def test_decodes_shell_overlay_slot_from_icon_index(self):
		self.assertEqual(3, _decode_overlay_index((3 << 24) | 42))
		self.assertIsNone(_decode_overlay_index(42))

	def test_pixmap_is_cached_per_overlay_index(self):
		overlays = object.__new__(ShellOverlays)
		overlays._cache = {}
		overlays._lock = Lock()
		overlays._load_pixmap = Mock(return_value='pixmap')

		first = overlays.pixmap(3)
		second = overlays.pixmap(3)

		self.assertIs(first, second)
		overlays._load_pixmap.assert_called_once_with(3)

	def test_com_initialization_happens_once_per_thread(self):
		overlays = object.__new__(ShellOverlays)
		overlays._com = local()
		pythoncom = Mock()
		with patch.dict(sys.modules, {'pythoncom': pythoncom}):
			overlays._initialize_com_for_thread()
			overlays._initialize_com_for_thread()

		pythoncom.CoInitialize.assert_called_once_with()

	def test_extracts_overlay_from_cached_system_image_list(self):
		overlays = object.__new__(ShellOverlays)
		overlays._com = local()
		overlays._image_list = 123
		overlays._comctl32 = Mock()
		overlays._comctl32.ImageList_GetIcon.return_value = 456
		overlays._user32 = Mock()
		qt_win = Mock()
		with patch.dict(
			sys.modules,
			{'PyQt5.QtWinExtras': SimpleNamespace(QtWin=qt_win)}
		), patch.object(overlays, '_initialize_com_for_thread'), \
			patch.object(overlays, '_get_overlay_image_index', return_value=4):
			result = overlays._load_pixmap(2)

		self.assertIs(qt_win.fromHICON.return_value, result)
		overlays._comctl32.ImageList_GetIcon.assert_called_once_with(
			123, 4, 1
		)
		overlays._user32.DestroyIcon.assert_called_once_with(456)
