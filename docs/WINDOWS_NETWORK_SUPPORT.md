# Windows network drives

Opening a UNC path (`\\server\share`, or an RDP-redirected drive such as
`\\tsclient\C\...`) used to make the **whole window** unresponsive — both panes,
not just the one showing the share — and it stayed sluggish for as long as the
share was open. fman now keeps the UI responsive there and fills the listing in
far fewer network round trips.

## Why it was slow

On a local disk a file-attribute lookup costs microseconds. On a UNC or
RDP-redirected share every one is a network round trip (milliseconds to tens of
milliseconds). Three code paths multiplied that per file:

1. **Hidden-file filtering ran on the GUI thread and did its own I/O.** The
   default hidden-file filter called `QFileInfo(path).isHidden()`, which is
   uncached and does not go through fman's cached `stat`. The filter is invoked
   as `Model._accepts` from `RecordFiles._preprocess_existing` (up to three
   times per file) and from `SortFilterTableModel.update()` over every row —
   both reached through `@run_in_main_thread` methods. One blocking network call
   per file, on the thread that also paints both panes. That was the freeze.
2. **The background loader never gave up.** `Row.__eq__` ignores `is_loaded`,
   and a file whose `stat` fails yields the same empty Size/Modified cells as
   its unloaded placeholder — so `RecordFiles` saw no change and kept the row at
   `is_loaded = False`. `_load_remaining_files` re-submitted itself every 200 ms
   forever, re-issuing the failing calls and hopping into the GUI thread each
   time. This is what made the sluggishness permanent rather than a slow first
   load.
3. **One Windows shell icon lookup per file.** `.exe` and `.dll` icons are
   embedded in the file, so asking the shell for them reads the file over the
   wire. A folder like `platform-tools` is mostly such files.

## What fman does now

- **The hidden-file filter performs no I/O.** On Windows it reads
  `FILE_ATTRIBUTE_HIDDEN` from fman's own cached `stat`, which the model has
  already loaded to fill the Size and Modified columns — a cache hit, and it
  invalidates correctly with `fs.clear_cache(...)`. Behavior is unchanged:
  Windows hidden-ness is driven solely by the attribute (there is no dot-prefix
  rule there), so `.gitignore` stays visible and Git's hidden `.git` folder
  stays hidden. macOS and Linux keep using `QFileInfo.isHidden()`, which handles
  the dot-prefix and `UF_HIDDEN` rules.
- **A row that cannot be loaded is tried once**, not forever. An explicit
  reload (`Reload` / `Refresh`) retries it.
- **Files on a network path get a generic per-extension icon** — one shell
  lookup per extension instead of one per file, and nothing is read over the
  wire. Local paths are untouched.

## Getting real icons back on network drives

Run **Toggle network drive icons** (also listed as *Show real icons on network
drives*) from the command palette. It flips the setting, reloads both panes, and
persists across restarts. The setting lives in `Core Settings.json`:

```json
{
  "network_file_icons": true
}
```

Default is `false` (generic icons). Expect the slow, per-file behavior back on
high-latency shares while it is on.

## The network:// share list

Everything above is about `file://` UNC paths. The `network://` scheme — the
*Network...* entry in the drive list — is separate, and used to sit on an empty
pane for a long time with no sign that anything was happening. Three things
changed:

From the network overview, **Open native file manager** (F10) opens Explorer's
Network page. Inside `network://SERVER`, it opens `\\SERVER`.

- **The browse-list walk no longer opens servers.** `NetworkFileSystem` only
  descends into containers (providers, domains/workgroups). It used to recurse
  into every resource it enumerated, so listing the root opened a connection to
  every discovered server — each unreachable one blocking for seconds — and
  then threw away everything that was not a direct child of the requested path.
  Shares are still listed: they are the direct children of the server handle one
  level down, so no share gets opened either.
- **Rows appear while the directory is still being enumerated.** The model used
  to drain `iterdir(...)` completely before committing a single row. It now
  flushes what it has every 0.5 s. A directory that lists faster than that never
  reaches the first flush, so local listings are unchanged. Neither does one
  that yields more than 1000 files in those 0.5 s (`_INIT_BATCH_MAX_FILES`):
  that is a fast file system with a huge directory, and streaming it froze the
  GUI thread — a local folder with 37,000 entries took over a minute of
  main-thread time. It is committed once, at the end, as before. See
  [LARGE_DIRECTORIES.md](LARGE_DIRECTORIES.md).
- **A slow pane says so, and keeps saying it.** After 0.4 s without rows, the
  pane paints a message in its centre: a title, then a line naming what it is
  waiting on, with a seconds counter that ticks every 0.4 s. The counter is the
  part that matters — a message that never changes reads as a frozen
  application. The initial delay is what keeps fast local directories from
  flashing it.

The indicator is not Windows-only, but its `network://` wording is. On a
`network://` pane it reads:

```
Searching network shares…

Waiting for Windows to return the network browse list (14 s).
A machine that is switched off or unreachable can hold this up.
```

Every other scheme — and therefore everything on macOS and Linux — gets the
generic form:

```
Loading…

Still reading this folder (2 s).
```

`network://` cannot occur on macOS or Linux at all: `NetworkFileSystem` is
imported under the `PLATFORM == 'Windows'` gate in `core/fs/local/__init__.py`,
and both places that mint such a URL — `DrivesFileSystem.resolve` and the
UNC-server bounce in `LocalFileSystem.resolve` — sit behind the same gate. An
SMB share mounted there is an ordinary `file://` path (`/Volumes/...`,
`/mnt/...`, gvfs), so a slow one gets the generic message. Of the two speed
fixes above, row streaming is platform-independent; the browse-list pruning is
Windows-only because that code is.

## Connecting to a share

On Windows, enter `smb://server/share` in **Go To** to open a share. The
`\\server\share` and `//server/share` forms work there too. Entering only
`smb://server` opens that server's share list. fman asks Windows to make the
connection, so the share remains a normal `file://` path and copying, Robocopy,
and the network-drive performance improvements continue to work.

When Windows needs credentials, its own login window appears above fman. The
**Remember** checkbox stores credentials in Windows Credential Manager; fman
does not see or store the password. Cancel leaves the address available in
Visited Paths without navigating.

The command palette has **Connect to network share** and **Disconnect network
share**. Connect accepts an optional drive letter such as `Z:`. A mapped drive
letter is saved by Windows and returns after restart; a connection without a
letter lasts only until sign-out or restart. Disconnect refuses while files on
the share are open and shows Windows' error so you can close them and try again.
These commands and SMB address handling are Windows-only.

## Known remaining slow paths

Neither freezes the UI, but both are worth knowing about:

- `LocalFileSystem.iterdir` uses `os.listdir` and then stats each entry
  separately — N round trips where `os.scandir` would need one. Not changed
  because on Windows `DirEntry.stat()` reports `st_dev`/`st_ino` as `0`, and
  `_prepare_move` compares `st_dev` to choose between a cheap rename and a full
  copy; seeding the cache with zeros would break cross-volume moves.
- `GoToListener.on_path_changed` calls `os.path.isdir` over the entries of
  `Visited Paths.json` under a 0.01 s budget that is only checked *between*
  calls. Once a `\\tsclient\...` path is in that history, a path change in
  either pane can block on it.
- `LocalFileSystem.resolve` is uncached and expensive on UNC, but runs once per
  navigation rather than per file.

## Implementation

- `src/main/resources/base/Plugins/Core/core/commands/hidden_files.py` —
  `_hidden_file_filter(url)` reads `query(url, 'stat').st_file_attributes` on
  Windows and treats any `OSError` as "not hidden" (the file still shows).
- `src/main/resources/base/Plugins/Core/core/commands/window.py` —
  `ToggleNetworkIcons` is an `ApplicationCommand`, so it registers by MRO like
  every other command in the package; it writes `_NETWORK_ICONS_KEY` via
  `core/settings.py`'s `save_setting` (passing `None` to clear the key when
  returning to the default) and then calls `pane.reload()` on each pane —
  `Model.reload()` already clears the FS cache for that location, which is where
  the icons computed under the old setting are held.
- `src/main/python/fman/impl/model/model.py` — `Model._load_attempted` records
  the rows `_load_remaining_files(...)` has tried; `reload()` clears it.
- `src/main/python/fman/impl/model/icon_provider.py` — `get_icon(...)` splits
  into `_get_file_icon(...)` and `_get_generic_icon(...)`. The latter is the
  folder-icon / per-suffix surrogate path that already existed for non-`file://`
  schemes; UNC paths now reuse it. `_is_network_path(path)` checks
  `path.startswith('//')` — `splitscheme(...)` hands over the forward-slash
  form, so `\\server\share` arrives as `//server/share`.
  `_network_icons_enabled()` reads the setting through `fman.load_json`, which
  is memoised, so the per-file cost is a dict lookup. The key name is
  deliberately restated in both modules rather than shared: a common constant
  would make `fman.impl` depend on the bundled Core plugin.
- `src/main/resources/base/Plugins/Core/core/fs/local/windows/network.py` —
  `_iter_handle(...)` recurses only into names that are *not* UNC-prefixed
  (`\\name`, i.e. a server or a share).
  `already_visited` stays: it still guards container cycles.
- `src/main/python/fman/impl/model/model.py` — `_init(...)` collects a batch
  alongside `files` and hands it to the existing `_record_files(...)` /
  `RecordFiles` path every `_INIT_BATCH_SECS`, unless the batch exceeds
  `_INIT_BATCH_MAX_FILES`. `RecordFiles` inserts new files that land in the same
  gap as one run, and `Rows` (`table.py`) rebuilds its key index lazily in
  `find(...)` instead of shifting it on every insert — both so that a flush of
  hundreds of files stays cheap. The final `_on_rows_inited(...)`
  still runs and is still authoritative: `set_rows(...)` is a full diff, so the
  intermediate inserts converge. `reload()` is deliberately not batched — it
  keeps the old rows on screen while it re-enumerates.
- `src/main/python/fman/impl/view/__init__.py` —
  `FileListView.set_loading(text)` plus a `drawText` in `paintEvent(...)`, drawn
  only while `rowCount() == 0`, so it disappears by itself once the first batch
  lands. The colour comes from `QPalette.Disabled`/`QPalette.Text`, so it follows
  the active theme without new QSS.
- `src/main/python/fman/impl/widgets.py` — `DirectoryPaneWidget` starts a
  repeating `QTimer` in `_on_location_changed(...)` and stops it in
  `_on_location_loaded(...)`, which also fires for an empty directory. Each tick
  re-renders `format_loading_message(...)` with the elapsed seconds, so the same
  interval serves as both the initial delay and the redraw rate. The error path
  needs nothing: `location_disappeared` navigates elsewhere, which produces a
  fresh `location_changed`.
- Tests:
  - `src/main/resources/base/Plugins/Core/core/tests/commands/test_hidden_files.py`
    (`HiddenFileFilterTest` — hidden, not hidden, failing `stat`, and that a
    non-`file://` URL is never stat'ed)
  - `src/main/resources/base/Plugins/Core/core/tests/fs/test_network.py`
    (`NetworkFileSystemTest` — the root lists servers without opening one, and
    a server lists its shares without opening one). Windows-only; skipped
    elsewhere.
  - `src/unittest/python/fman_unittest/impl/model/test_model.py`
    (`LoadRemainingFilesTest` — an unloadable row is attempted once, and a
    reload retries it; `InitStreamsFilesTest` — a slow listing shows rows
    before it finishes, a fast one still commits only at the end)
  - `src/unittest/python/fman_unittest/impl/model/test_icon_provider.py`
    (`NetworkIconTest` — local files keep the shell icon, network files share
    one icon per suffix, and the setting restores the shell icon)
  - `src/unittest/python/fman_unittest/impl/test_widgets.py`
    (`FormatLoadingMessageTest` — the indicator carries whole elapsed seconds
    below its title)
