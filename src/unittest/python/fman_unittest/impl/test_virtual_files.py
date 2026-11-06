import struct
import unittest
from unittest.mock import Mock

from fbs_runtime.platform import is_windows

if not is_windows():
	raise unittest.SkipTest('Virtual files are only available on Windows')

from fman.impl import virtual_files


class TestVirtualFiles(unittest.TestCase):
	def _descriptor(self, name, attributes=0, size=0):
		entry = bytearray(592)
		struct.pack_into('<I', entry, 36, attributes)
		struct.pack_into('<II', entry, 64, size >> 32, size & 0xffffffff)
		encoded_name = name.encode('utf-16le') + b'\0\0'
		entry[72:72 + len(encoded_name)] = encoded_name
		return bytes(entry)

	def test_parses_names_attributes_and_sizes(self):
		blob = struct.pack('<I', 2) + self._descriptor('folder', 0x14) + \
			self._descriptor('large.bin', 0x40, 0x123456789)
		files = virtual_files._parse_file_group_descriptor(blob)
		self.assertEqual([
			{'name': 'folder', 'is_directory': True, 'size': None},
			{'name': 'large.bin', 'is_directory': False, 'size': 0x123456789}
		], files)

	def test_sanitizes_paths_and_disambiguates_names(self):
		used = {}
		self.assertEqual('unnamed', virtual_files._sanitize_name('..', used))
		self.assertEqual('C_/secret.txt', virtual_files._sanitize_name(
			r'C:\secret.txt', used))
		self.assertEqual('folder/file.txt', virtual_files._sanitize_name(
			r'folder\file.txt', used))
		self.assertEqual('file.txt', virtual_files._sanitize_name(
			'file.txt', used))
		self.assertEqual('file (2).txt', virtual_files._sanitize_name(
			'file.txt', used))
		self.assertEqual('FILE (3).TXT', virtual_files._sanitize_name(
			'FILE.TXT', used))
		self.assertEqual('unnamed (2)', virtual_files._sanitize_name('', used))
		self.assertEqual('a____/___', virtual_files._sanitize_name(
			'a<>:"/|?*', used))
		self.assertEqual('_CON', virtual_files._sanitize_name('CON', used))

	def test_sanitizes_file_directory_prefix_collisions_in_either_order(self):
		for entries, expected in (
			([('Report', False), ('report/attachment.txt', False)],
			 ['Report', 'report (2)/attachment.txt']),
			([('report/attachment.txt', False), ('Report', False)],
			 ['report/attachment.txt', 'Report (2)'])
		):
			used = {}
			paths = [virtual_files._sanitize_name(name, used, is_directory)
				for name, is_directory in entries]
			self.assertEqual(expected, paths)

	def test_saves_hglobal_and_stream_contents(self):
		import pythoncom

		blob = struct.pack('<I', 2) + self._descriptor('memory.bin', 0x40, 3) + \
			self._descriptor('stream.bin', 0x40, 6)
		stream = pythoncom.CreateStreamOnHGlobal(None, True)
		stream.Write(b'stream')
		stream.Seek(0, 0)
		data_object = _fake_data_object(blob, [
			(pythoncom.TYMED_HGLOBAL, b'abc-too-long'),
			(pythoncom.TYMED_ISTREAM, stream)
		])

		paths = virtual_files.save_virtual_files(data_object)
		self.assertEqual(2, len(paths))
		from fman.url import as_human_readable
		first, second = map(as_human_readable, paths)
		with open(first, 'rb') as file:
			self.assertEqual(b'abc', file.read())
		with open(second, 'rb') as file:
			self.assertEqual(b'stream', file.read())

	def test_saves_storage_as_a_compound_file(self):
		import pythoncom
		from win32com import storagecon

		flags = storagecon.STGM_CREATE | storagecon.STGM_READWRITE | \
			storagecon.STGM_SHARE_EXCLUSIVE
		source = pythoncom.StgCreateDocfile(None, flags, 0)
		stream = source.CreateStream('payload', flags, 0, 0)
		stream.Write(b'email body')
		stream.Commit(0)
		blob = struct.pack('<I', 1) + self._descriptor('message.msg')
		data_object = _fake_data_object(blob, [(pythoncom.TYMED_ISTORAGE, source)])

		path = virtual_files.save_virtual_files(data_object)[0]
		from fman.url import as_human_readable
		storage = pythoncom.StgOpenStorage(
			as_human_readable(path), None,
			storagecon.STGM_READ | storagecon.STGM_SHARE_EXCLUSIVE, None, 0)
		stored_stream = storage.OpenStream(
			'payload', None,
			storagecon.STGM_READ | storagecon.STGM_SHARE_EXCLUSIVE, 0)
		self.assertEqual(b'email body', stored_stream.Read(100))

	def test_reports_missing_descriptor(self):
		data_object = Mock()
		data_object.QueryGetData.side_effect = OSError('not supported')
		self.assertFalse(virtual_files.has_virtual_files(data_object))


def _fake_data_object(descriptor, contents):
	import pythoncom
	from win32com.server.util import wrap

	class DataObject:
		_com_interfaces_ = [pythoncom.IID_IDataObject]
		_public_methods_ = [
			'QueryGetData', 'GetData', 'GetDataHere', 'GetCanonicalFormatEtc',
			'SetData', 'EnumFormatEtc', 'DAdvise', 'DUnadvise', 'EnumDAdvise'
		]

		def QueryGetData(self, formatetc):
			return None

		def GetData(self, formatetc):
			medium = pythoncom.STGMEDIUM()
			if formatetc[0] == virtual_files._clipboard_format(
				virtual_files.FILE_GROUP_DESCRIPTOR_FORMAT):
				medium.set(pythoncom.TYMED_HGLOBAL, descriptor)
			else:
				tymed, data = contents[formatetc[3]]
				medium.set(tymed, data)
			return medium

	return wrap(DataObject(), pythoncom.IID_IDataObject)
