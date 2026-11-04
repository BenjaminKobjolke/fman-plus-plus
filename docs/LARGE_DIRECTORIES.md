# Large Directories

How a pane loads a directory with tens of thousands of entries, and what keeps
the rest of the app responsive while it does.

The reference case is a Windows `%TEMP%` folder with 37,328 entries, 35,673 of
them subfolders. Opening it used to make the **whole window** sluggish — the
cursor, typing, even the other pane — because both panes share one GUI thread
and the loading pane kept that thread busy.

## How a pane loads

Each pane's `Model` owns one worker thread. The worker does the file system
work and hands finished data to the GUI thread to commit.

1. **Listing.** `Model._init(...)` walks `iterdir(...)`. For every entry it
   loads the name and the value of the current sort column — on a local drive,
   one `os.stat` per entry.
2. **First commit.** The sorted rows are committed in one go. Only the rows
   that fit on screen are fully loaded at this point.
3. **Background load.** `_load_remaining_files(...)` then loads everything
   else — icon, size, modified date — for *every* row, not just the visible
   ones. It works in slices of 0.2 s and commits each slice on the GUI thread.

A slow file system gets one extra step: if the listing takes longer than 0.5 s,
`_init(...)` shows what it has so far instead of leaving the pane empty. That
is described in [WINDOWS_NETWORK_SUPPORT.md](WINDOWS_NETWORK_SUPPORT.md).

## What keeps it responsive

Four things, all in the GUI thread's path. The numbers are for 37,000 rows.

### The vertical header is `Fixed`

Every row has the same height, and `UniformRowHeights` computes it once. The
vertical header (hidden, but it still owns the row heights) used to be in
`ResizeToContents` mode all the same. In that mode Qt re-measures **every** row
whenever the model reports changed data — which the background load does five
times a second. Each pass was 37,000 calls into Python.

| Vertical header mode | GUI thread time per background commit |
|---|---|
| `ResizeToContents` | 0.33 s |
| `Fixed` | 0 s |

With a commit every 0.2 s costing 0.33 s, the GUI thread never caught up until
the last row was loaded. This was the lag that outlasted the listing.

A `Fixed` header never asks the view how tall a row is, so the view tells it:
`get_row_height()` calls `setDefaultSectionSize(...)` whenever it computes a new
height, and the icon-size handler recomputes right away. Ported from
RoyiFileManager 0.8.0 — see [ROYI_SYNC.md](ROYI_SYNC.md).

### A huge, fast listing is not streamed

The early rows of a slow listing are spliced in between the rows already shown,
and each gap that receives files costs one Qt insert. In a pane sorted by name
that is a handful of gaps. In a pane sorted by size or modified date the
listing order has nothing to do with the sort order, so nearly every file lands
in a gap of its own: thousands of inserts per flush, seconds of frozen GUI
thread.

So `_init(...)` only streams batches of up to `_INIT_BATCH_MAX_FILES` (1000)
files. More than that in 0.5 s means the file system is fast and the directory
is huge; the listing will be over in a few seconds anyway, and it is committed
once at the end.

The visible effect: a huge local folder shows the loading text until it is
completely listed (about 3 s for the reference folder) rather than filling in
after 0.5 s.

### New files are inserted as runs

`RecordFiles` is what adds files to a pane that already shows some: a streamed
batch, or a file created while you watch. It used to emit one insert per file.
It now sorts the new files, groups the ones that land in the same gap, and
inserts each group at once.

It also sorts by the sort value alone. Sorting `(sort value, file)` pairs
raised `TypeError` as soon as two new files had the same sort value, because
files cannot be ordered — easy to hit in a pane sorted by size.

### The key index is rebuilt lazily

`Rows` keeps a `key -> row number` dictionary so a file's row can be found
without searching. Every insert or removal used to shift the number of every
later row, in a Python loop: O(n) per call, and 91% of the time when thousands
of rows were inserted one after the other. An insert or removal now just drops
the dictionary; `find(...)` rebuilds it the next time someone asks.

## Shell icons are fetched by the worker

On Windows, `QFileIconProvider.icon()` returns a lazy icon. The actual shell
lookup happens when Qt first paints it, on the GUI thread; repainting program
icons can ask the shell again. In a current Windows 11 profile (Qt 5.15.2,
PyQt5 5.15.11, Python 3.14), listing ordinary folders took under 5 ms, while
the first GUI-thread pixmap pass took seconds in cold shell caches. Painting
one screen of System32 program rows took 42–54 ms per paint with lazy icons,
versus 5–6 ms with finished pixmaps.

| Directory | Entries | `os.listdir` | `os.stat` all | Shell icon provider | First `pixmap()` pass | Repaint `pixmap()` pass |
|---|---:|---:|---:|---:|---:|---:|
| `C:\Windows\System32` | 5272 | 2.6 ms | 110 ms | 6.7 ms | 3178 ms | 765 ms |
| `C:\Windows` | 127 | 0.2 ms | 2.6 ms | 0.2 ms | 256 ms | 10 ms |
| Downloads, cold shell cache | 34 | 0.1 ms | 4.7 ms | 0.1 ms | 3561 ms | 11 ms |
| Downloads, warm shell cache | 34 | – | – | – | 64 ms | 10 ms |
| fman source directory | 57 | 0.1 ms | 0.7 ms | 0.1 ms | 14 ms | 0.1 ms |

`ShellIconProvider` now asks the shell and materializes 16, 32 and 48 px
pixmaps in the pane worker. Ordinary files share a finished icon per suffix;
folders and `.exe`, `.lnk` and `.ico` retain their own icons. A lock serializes
the two panes' calls into Qt's shared shell helper thread. At the 64 px view
cap, Qt scales the 48 px pixmap; add another size if that looks soft.

Repeat the profile in a Windows desktop session (the first run after boot
measures a cold shell cache):

```bash
uv run python tools/profile_directory_phases.py "C:\Windows\System32" "%USERPROFILE%\Downloads"
```

The tool separates enumeration, stat, lazy icon lookup, first and second
pixmap passes, worker-side materialization and table painting. It also checks
that every materialized 16 px image matches Qt's lazy icon.

## Known remaining slow paths

Not fixed, because none of them blocks the GUI thread for long. Measure before
changing any of them: `python -m fman.main --profile`.

- **One `os.stat` per entry.** `LocalFileSystem.iterdir(...)` uses
  `os.listdir`, which throws away the attributes Windows returns while
  enumerating. Listing the reference folder is 0.14 s; the stats that follow
  are 2.6 s. `os.scandir` would deliver both in 0.2 s, but on Windows
  `DirEntry.stat()` reports `st_dev` and `st_ino` as 0, and the cached `stat`
  feeds the same-device check in `_prepare_move(...)` and `samefile(...)`.
  Filling the cache from it would silently turn renames into copy + delete.
- **Every row is loaded in the background**, visible or not. Several seconds of
  worker time, competing with the GUI thread for the interpreter lock.
- **Every pane reloads when fman becomes the active window** — the stand-in for
  a file watcher, which fman does not run on Windows. A reload clears the
  directory's cache and repeats the listing and the load of every row.

## Implementation

- `src/main/python/fman/impl/view/__init__.py` —
  `FileListView._init_vertical_header()` sets the header to `Fixed`.
- `src/main/python/fman/impl/view/uniform_row_heights.py` —
  `get_row_height()` and `_on_icon_size_changed(...)` hand the height to the
  header.
- `src/main/python/fman/impl/model/model.py` — `_INIT_BATCH_SECS`,
  `_INIT_BATCH_MAX_FILES` and the flush in `_init(...)`.
- `src/main/python/fman/impl/model/record_files.py` — `RecordFiles.__call__()`
  groups the inserts.
- `src/main/python/fman/impl/model/table.py` — `Rows`, the lazy `_keys`.
- `src/main/python/fman/impl/model/shell_icons.py` — materializes Windows shell
  icons in the pane worker.
- `tools/profile_directory_phases.py` — measures directory loading and icon
  painting phases.

## Tests

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_model_tests.bat'"
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_view_tests.bat'"
```

- `test_model.py` — `ModelRecordFilesTest.test_new_files_are_inserted_as_runs`,
  `test_new_files_with_equal_sort_values`;
  `InitStreamsFilesTest.test_huge_fast_listing_commits_once`.
- `test_table.py` — `RowsFindTest`: `find(...)` after insert, remove, move and
  update.
- `test_shell_icons.py` — Windows shell icon caching, materialization and
  worker-thread loading.
- `uniform_row_heights_test.py` — the header gets the row height, also after
  the icon size changes. A `*_test.py` file: it needs a `QApplication` of its
  own and stays out of `python build.py test`.

None of these measures time. To check the effect by hand, open a folder with
tens of thousands of entries, then move the cursor, type, and use the other
pane while and after it fills. Repeat with the pane sorted by modified date,
and after switching away from fman and back.
