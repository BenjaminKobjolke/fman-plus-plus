from fman import PLATFORM
from unittest import TestCase, skipIf

if PLATFORM == 'Windows':
	from core.fs.local.windows.drives import (
		DriveFree, DriveName, DriveSize, DrivesFileSystem
	)
else:
	DriveName = None
	DriveSize = None
	DriveFree = None
	DrivesFileSystem = None


@skipIf(PLATFORM != 'Windows', 'drives:// only exists on Windows')
class DriveNameTest(TestCase):
	def test_does_not_query_volume_label_for_a_network_drive(self):
		from unittest.mock import patch

		class Kernel32:
			volume_info_calls = 0
			def GetDriveTypeW(self, path):
				return 4
			def GetVolumeInformationW(self, *args):
				self.volume_info_calls += 1
				return 0

		class Windll:
			kernel32 = Kernel32()

		with patch('core.fs.local.windows.drives.windll', Windll()):
			self.assertEqual('Z:', DriveName().get_str('drives://Z:'))
		self.assertEqual(0, Windll.kernel32.volume_info_calls)


@skipIf(PLATFORM != 'Windows', 'drives:// only exists on Windows')
class DriveSpaceTest(TestCase):
	def test_default_columns_include_drive_name_size_and_free(self):
		self.assertEqual(
			(
				DriveName.__module__ + '.DriveName',
				DriveSize.__module__ + '.DriveSize',
				DriveFree.__module__ + '.DriveFree',
			),
			DrivesFileSystem().get_default_columns('')
		)

	class Kernel32:
		def __init__(self, drive_type=0):
			self.drive_type = drive_type
		def GetDriveTypeW(self, path):
			return self.drive_type
		def GetVolumeInformationW(self, *args):
			return 0

	class Windll:
		def __init__(self, drive_type=0):
			self.kernel32 = DriveSpaceTest.Kernel32(drive_type)

	def test_size_and_free_columns_format_disk_usage(self):
		from types import SimpleNamespace
		from unittest.mock import patch

		usage = SimpleNamespace(
			total=500 * 1024 ** 3, used=380 * 1024 ** 3, free=120 * 1024 ** 3
		)
		with patch('core.fs.local.windows.drives.windll', self.Windll()), \
				patch(
					'core.fs.local.windows.drives.shutil.disk_usage',
					return_value=usage,
				) as disk_usage:
			self.assertEqual('500.0 GB', DriveSize().get_str('drives://C:'))
			self.assertEqual('120.0 GB', DriveFree().get_str('drives://C:'))
		self.assertEqual(2, disk_usage.call_count)
		disk_usage.assert_called_with('C:\\')

	def test_network_entry_is_blank_and_sorts_last(self):
		from unittest.mock import patch

		with patch('core.fs.local.windows.drives.shutil.disk_usage') as disk_usage:
			self.assertEqual('', DriveSize().get_str('drives://Network...'))
			self.assertEqual('', DriveFree().get_str('drives://Network...'))
			disk_usage.assert_not_called()
		self.assertEqual(
			(True, 0), DriveSize().get_sort_value('drives://Network...', True)
		)

	def test_remote_drive_is_blank_without_disk_usage(self):
		from unittest.mock import patch

		with patch('core.fs.local.windows.drives.windll', self.Windll(4)), \
				patch(
					'core.fs.local.windows.drives.shutil.disk_usage'
				) as disk_usage:
			self.assertEqual('', DriveSize().get_str('drives://Z:'))
			self.assertEqual('', DriveFree().get_str('drives://Z:'))
			disk_usage.assert_not_called()

	def test_disk_usage_oserror_returns_blank(self):
		from unittest.mock import patch

		with patch('core.fs.local.windows.drives.windll', self.Windll()), \
				patch(
					'core.fs.local.windows.drives.shutil.disk_usage',
					side_effect=OSError,
				):
			self.assertEqual('', DriveSize().get_str('drives://D:'))
			self.assertEqual('', DriveFree().get_str('drives://D:'))

	def test_sort_value_uses_bytes_and_unknown_is_zero(self):
		from types import SimpleNamespace
		from unittest.mock import patch

		usage = SimpleNamespace(total=100, used=75, free=25)
		with patch('core.fs.local.windows.drives.windll', self.Windll()), \
				patch(
					'core.fs.local.windows.drives.shutil.disk_usage',
					return_value=usage,
				):
			self.assertEqual(
				(False, 100), DriveSize().get_sort_value('drives://C:', True)
			)
			self.assertEqual(
				(False, 25), DriveFree().get_sort_value('drives://C:', True)
			)
		with patch('core.fs.local.windows.drives.windll', self.Windll()), \
				patch(
					'core.fs.local.windows.drives.shutil.disk_usage',
					side_effect=OSError,
				):
			self.assertEqual(
				(False, 0), DriveSize().get_sort_value('drives://D:', True)
			)
