"""Native Robocopy tests; destination-junction/ADS behavior needs a separate
manual check."""

import ctypes
import os
from pathlib import Path
from unittest import skipUnless

from robocopy_plugin import jobs, logs, planner, settings, windows
from robocopy_integration_base import RobocopyFixture


@skipUnless(os.name == 'nt', 'robocopy.exe is Windows-only')
class RobocopyEngineIT(RobocopyFixture):
	def test_loopback_unc_loose_files_copy_and_move(self):
		local_source = self.source
		unc = Path(
			'\\\\localhost\\' + local_source.drive[0] + '$'
			+ str(local_source)[2:]
		)
		try:
			if not unc.is_dir():
				self.skipTest('Loopback administrative share unavailable')
		except OSError as error:
			self.skipTest('Loopback administrative share unavailable: %s' % error)
		self.source = unc
		for move in (False, True):
			with self.subTest(move=move):
				name = 'move.txt' if move else '\u00e9tude.txt'
				(local_source / name).write_bytes(b'UNC fixture')
				(local_source / 'unselected.txt').write_bytes(b'keep')
				self.run_plan(self.plan((name,), move=move))
				self.assertEqual(b'UNC fixture', (self.destination / name).read_bytes())
				self.assertEqual(not move, (local_source / name).exists())
				self.assertFalse((self.destination / 'unselected.txt').exists())

	def test_hyphen_directory_copy_and_move(self):
		for move in (False, True):
			with self.subTest(move=move):
				name = '-move' if move else '-copy'
				(self.source / name).mkdir()
				(self.source / name / 'inside.txt').write_bytes(b'folder')
				self.run_plan(self.plan((name,), move=move))
				self.assertEqual(
					b'folder', (self.destination / name / 'inside.txt').read_bytes()
				)
				self.assertEqual(not move, (self.source / name).exists())

	def test_exact_mixed_selection_and_two_unicode_log_appends(self):
		names = (
			'file with space.txt', 'note', '[brackets].txt', '@leading.txt',
			'\u00e9tude.txt'
		)
		for name in (*names, 'note.txt', 'unselected.txt'):
			(self.source / name).write_bytes(name.encode())
		(self.source / 'Photos' / 'empty').mkdir(parents=True)
		(self.source / 'Photos' / 'picture.bin').write_bytes(b'picture')
		options = settings.Settings(log_enabled=True, retries=0)
		planner.probe(self.executable, options)
		path = logs.choose_path(str(self.root / 'settings'))
		plan = self.plan((*names, 'Photos'), options=options, log=path)
		log = logs.TransferLog(path, 'Copy fixture')
		for index, job in enumerate(plan.jobs):
			log.append('Job %d' % (index + 1))
			planner.recheck(plan, job)
			code, output = windows.run(
				job.arguments(self.executable, options, log=path), timeout=15
			)
			self.assertLess(code, 8, output)
			log.validate()
		log.finish('Completed fixture')
		self.assertEqual(
			set((*names, 'Photos')),
			{path.name for path in self.destination.iterdir()}
		)
		for name in names:
			self.assertEqual(
				(self.source / name).read_bytes(),
				(self.destination / name).read_bytes()
			)
		self.assertTrue((self.destination / 'Photos' / 'empty').is_dir())
		text = log.path.read_text(encoding='utf-16')
		for marker in ('Job 1', 'Job 2', '\u00e9tude.txt', 'Completed fixture'):
			self.assertIn(marker, text)
		self.assertNotIn('\ufeff', text)

	def test_native_equal_metadata_move_keeps_source(self):
		self.destination.mkdir()
		source, destination = self.source / 'same.txt', self.destination / 'same.txt'
		source.write_bytes(b'aaaa')
		destination.write_bytes(b'bbbb')
		stamp = source.stat().st_mtime_ns
		os.utime(destination, ns=(stamp, stamp))
		plan = self.plan(('same.txt',), move=True)
		self.assertEqual([0], self.run_plan(plan))
		self.assertEqual(b'aaaa', source.read_bytes())
		self.assertEqual(b'bbbb', destination.read_bytes())
		self.assertEqual(
			(1, 0, (str(source),)), planner.remaining(plan.jobs[0].entries)
		)

	def test_forced_small_native_batches_never_include_unselected_files(self):
		names = tuple('selected %d.txt' % index for index in range(12))
		for name in (*names, 'unselected.txt'):
			(self.source / name).write_bytes(name.encode())
		plan = self.plan(names)
		entries = plan.jobs[0].entries
		limit = jobs.command_units(
			jobs.Job(plan.source, plan.destination, (), (names[0],)).arguments(
				self.executable, plan.settings
			)
		) + 40
		batches = jobs.build_jobs(
			plan.source, plan.destination, entries, self.executable,
			plan.settings, limit=limit
		)
		self.assertGreater(len(batches), 1)
		for job in batches:
			arguments = job.arguments(self.executable, plan.settings)
			self.assertLessEqual(jobs.command_units(arguments), limit)
			code, output = windows.run(arguments, timeout=15)
			self.assertLess(code, 8, output)
		self.assertEqual(set(names), {path.name for path in self.destination.iterdir()})
		for name in names:
			self.assertEqual(name.encode(), (self.destination / name).read_bytes())

	def test_move_files_and_empty_selected_directory_not_pane_root(self):
		(self.source / 'move.txt').write_bytes(b'move')
		(self.source / 'keep.txt').write_bytes(b'keep')
		(self.source / 'Empty').mkdir()
		plan = self.plan(('move.txt', 'Empty'), move=True)
		self.run_plan(plan)
		self.assertEqual({'keep.txt'}, {path.name for path in self.source.iterdir()})
		self.assertEqual(
			{'move.txt', 'Empty'},
			{path.name for path in self.destination.iterdir()}
		)
		for job in plan.jobs:
			self.assertEqual((0, 0, ()), planner.remaining(job.entries))

	def test_native_overwrite_newer_and_destination_hardlink_effect(self):
		self.destination.mkdir()
		source = self.source / 'report.txt'
		destination = self.destination / 'report.txt'
		source.write_bytes(b'new source content')
		destination.write_bytes(b'old')
		os.utime(source, (1600000000, 1600000000))
		os.utime(destination, (1700000000, 1700000000))
		alias = self.root / 'outside.txt'
		os.link(destination, alias)
		self.run_plan(self.plan(('report.txt',)))
		self.assertEqual(source.read_bytes(), destination.read_bytes())
		self.assertEqual(source.read_bytes(), alias.read_bytes())

	def test_self_descendant_source_replacement_and_log_overlap_refused(self):
		(self.source / 'Folder').mkdir()
		for target in (self.source, self.source / 'Folder' / 'child'):
			self.destination = target
			with self.assertRaises(ValueError):
				self.plan(('Folder',))
		self.destination = self.root / 'target'
		with self.assertRaisesRegex(ValueError, 'log'):
			self.plan(('Folder',), log=str(self.destination / 'log.txt'))
		plan = self.plan(('Folder',))
		(self.source / 'Folder').rename(self.source / 'old')
		(self.source / 'Folder').mkdir()
		with self.assertRaisesRegex(ValueError, 'replaced'):
			planner.recheck(plan, plan.jobs[0])
		self.assertFalse(self.destination.exists())


	def test_failed_native_move_overwrite_preserves_source(self):
		self.destination.mkdir()
		(self.source / 'locked.txt').write_bytes(b'source data')
		(self.destination / 'locked.txt').write_bytes(b'keep')
		plan = self.plan(('locked.txt',), move=True)
		library = windows.api()
		handle = library.CreateFileW(
			str(self.destination / 'locked.txt'), 0x80000000, 0, None, 3, 0, None
		)
		self.assertNotEqual(ctypes.c_void_p(-1).value, handle)
		try:
			code, output = windows.run(
				plan.jobs[0].arguments(self.executable, plan.settings, True),
				timeout=15
			)
			self.assertGreaterEqual(code, 8, output)
		finally:
			library.CloseHandle(handle)
		self.assertEqual(b'source data', (self.source / 'locked.txt').read_bytes())
		self.assertEqual(b'keep', (self.destination / 'locked.txt').read_bytes())
		self.assertEqual(1, planner.remaining(plan.jobs[0].entries)[0])
