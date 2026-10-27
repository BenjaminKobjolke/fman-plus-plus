# Video viewer

An in-pane viewer that plays a video directly inside the active pane,
replacing the file list until closed — the [text viewer](TEXT_VIEWER.md)'s
and [image viewer](IMAGE_VIEWER.md)'s counterpart for video files. It exists
so you can peek at a `.mp4`/`.mkv`/etc. without leaving fman or waiting on an
external player to launch. Always read-only, keyboard-controlled, no on-screen
sliders.

## Usage

1. Put the cursor on a video file and run **"View file"** from the command
   palette — the same command as the text and image viewers; see
   [`docs/functions/view-file.md`](../functions/view-file.md) for how it
   picks which viewer to open. (**"View file in other pane"** opens the video
   viewer in the opposite pane instead.)
2. The video fills the active pane, in place of the file list, and starts
   playing immediately. A `current / total` time readout
   (e.g. `0:12 / 3:45`) sits below it.
3. **Space** toggles play/pause. **Left**/**Right** seek 5 seconds back/
   forward. **Up**/**Down** adjust volume by 5, flashing the new level
   (`Volume: N`) briefly over the video via mpv's own on-screen display —
   there's still no persistent on-screen slider.
4. Press **Escape**, **Enter**, or **Backspace** to close the viewer and
   return to the file list, with the cursor back on the same file.
5. Press **Tab** to switch to the other pane — same as the normal file list.
   The viewer stays open (and keeps playing) in this pane; pressing **Tab**
   again brings focus straight back to it.
6. Press **Ctrl+Shift+P** to open the viewer's own command palette (see
   below) instead of closing with Escape/Enter/Backspace.

## Controls

Suitable file-list shortcuts such as F5 (Copy) also work while viewing a
video; see [shared viewer shortcuts](../KEYBINDINGS.md#file-list-shortcuts-that-also-work-in-a-viewer).

| Key                | Action                        |
|--------------------|-------------------------------|
| Space              | Play / pause                  |
| Left / Right       | Seek −5s / +5s                |
| Up / Down          | Volume +5 / −5 (0–100), flashes `Volume: N` on screen and in the status bar |
| Escape/Enter/Backspace | Close viewer               |
| Tab / Shift+Tab    | Switch panes                   |
| Ctrl+Shift+P       | Open viewer command palette    |

**Palette entries:** *Play / Pause*, *Restart*, *Mute / Unmute*,
*Reset volume*, *Exit viewer*. Mute has no default key — bind one yourself
(see [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings)).

**Every control reports itself twice:** as mpv's own on-video flash and in
the [status bar](../STATUSBAR.md) — `Playing` / `Paused`, `Restarted`,
`Volume: 60`, `Muted` / `Unmuted`. The OSD is easy to miss on a bright frame
and invisible if you're looking at the other pane; the status bar isn't.

**Volume and mute persist across sessions** — the last value set via
Up/Down, *Reset volume*, or *Mute / Unmute* is restored the next time any
video is opened (stored in `Core Settings.json`, the same mechanism as the
text/image viewers' remembered zoom level).

## Behaviour

- **Read-only.** There's no edit mode — same as the image viewer.
- **Per-pane, one at a time.** Opening a video while a text/image viewer (or
  another video) is open in that pane replaces it, and vice versa — all
  three share the same pane mount slot; the other pane is unaffected.
- **No zoom.** Unlike the text and image viewers, there's no font-size/scale
  zoom — a video fills the pane at its native aspect ratio.
- **Letterboxed with the pane's theme color**, same as the image viewer —
  not a hardcoded value; see [`docs/THEMES.md`](../THEMES.md).
- **Recognized extensions:** `.mp4`, `.m4v`, `.mkv`, `.webm`, `.avi`, `.mov`,
  `.wmv`, `.flv`, `.mpg`, `.mpeg`, `.ogv`, `.3gp`, `.ts`. Anything else opens
  in the [text viewer](TEXT_VIEWER.md) (or [image viewer](IMAGE_VIEWER.md)
  for image extensions) instead.

## Bindable commands

Every action above (default-keyed or not) is also a viewer-only pseudo-command
you can bind your own key to in your own `Viewer Key Bindings (<OS>).json` — a
**separate file** from `Key Bindings (<OS>).json`, see
[`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings) for the
full mechanism and an example. A user rebind always wins over the default key
listed in Controls above.

| Command                | Default key | Action                       |
|-------------------------|------------|-------------------------------|
| `video_toggle_pause`    | Space      | Play / pause                  |
| `video_seek_forward`    | Right      | Seek +5s                      |
| `video_seek_backward`   | Left       | Seek −5s                      |
| `video_volume_up`       | Up         | Volume +5                     |
| `video_volume_down`     | Down       | Volume −5                     |
| `video_mute`            | *(none)*   | Toggle mute                   |
| `video_reset_volume`    | *(none)*   | Volume → 100                  |
| `video_restart`         | *(none)*   | Restart from 0:00             |
| `viewer_close`          | Escape/Enter/Backspace | Close viewer       |
| `viewer_switch_panes`   | Tab        | Switch panes                  |
| `viewer_open_palette`   | Ctrl+Shift+P | Open viewer command palette |
| `viewer_next_file` / `viewer_previous_file` | *(none)* | View next / previous file in the directory |
| `viewer_toggle_same_type_advance` | *(none)* | Toggle "advance only for same type" |
| `viewer_delete_file` | *(none)* | Move the video to the trash |
| `viewer_rename_file` | *(none)* | Rename the video, keeping it playing |
| `viewer_toggle_close_after_delete` | *(none)* | Toggle whether a delete closes the viewer or goes to the next file |

Next/previous and the same-type toggle are **shared** across all three viewers
— see [File viewers](../viewers/FILE_VIEWERS.md#shared-behaviour) for how they
behave and [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings)
for suggested keys.

## Playback backend

Video is decoded and played by **[python-mpv](https://github.com/jaseg/python-mpv)**
(libmpv bindings), not `QtMultimedia`. libmpv bundles its own codecs, so
`mp4`/`mkv`/`webm`/`avi`/`mov` all play identically on Windows/macOS/Linux
without depending on whatever codecs happen to be installed on the OS.

- **Requires the native `libmpv` binary** (`libmpv-2.dll`/`mpv-2.dll`/
  `mpv-1.dll` on Windows; `libmpv.so`/`.dylib` elsewhere) discoverable at
  runtime. This is separate from the `python-mpv` pip package (in
  `pyproject.toml`), which is just the Python binding.
  - **Windows: auto-downloaded on first use, no manual setup.**
    `core/libmpv.py::ensure_libmpv_on_path()` checks
    `DATA_DIRECTORY/Local/libmpv/libmpv-2.dll`; if missing, it downloads a
    **pinned** LGPLv2.1+ build from
    [`zhongfly/mpv-winbuild`](https://github.com/zhongfly/mpv-winbuild)
    (deliberately not the more common
    [`shinchiro/mpv-winbuild-cmake`](https://github.com/shinchiro/mpv-winbuild-cmake)
    builds, which are GPL-2.0-or-later by default), verifies it by SHA-256,
    and extracts just the DLL with the project's bundled `7za.exe`. The DLL
    is never committed to the repo — only fetched from upstream, once, into
    the user data dir.
  - **Real progress dialog, not a status-bar message.** The download runs
    as an `fman.Task` submitted via `fman.submit_task` — the same mechanism
    `core/commands/` uses for copy/move/delete/rename — which
    pops a byte-accurate `QProgressDialog` (with a working Cancel button)
    once the download runs past ~1 second. `show_video_viewer()` is
    deliberately *not* `@run_in_main_thread`: fman already runs each
    `DirectoryPaneCommand.__call__` (and so `ViewFile`, its caller) on its
    own background thread
    (`PaneCommandRegistry._run_outside_main_thread`), and calling
    `ensure_libmpv_on_path()` from there — before ever touching Qt widgets —
    is what keeps the rest of the app responsive during the download instead
    of freezing on the main thread. Only the widget construction
    (`_open_video_view`) marshals onto the main thread, and only *after*
    libmpv is confirmed present — the video is never started while the DLL
    is still missing.
  - **Cancelling or failing the download aborts cleanly.** If the user
    cancels the progress dialog, or the download/hash-check/extraction
    fails, `ensure_libmpv_on_path()` raises rather than silently
    continuing; `show_video_viewer()` catches that and shows an alert
    instead of ever calling `import mpv` or opening the viewer.
  - Loading it prepends the cache dir to `%PATH%` (idempotently — guarded so
    repeated calls, e.g. opening several videos in one session, don't grow
    `%PATH%` unbounded). This matches what `python-mpv` itself needs: its
    own module-level lookup resolves the DLL via
    `ctypes.util.find_library()`, which on Windows scans `%PATH%` for the
    file and hands the resulting absolute path to `CDLL` — confirmed
    end-to-end during development (`os.add_dll_directory()` alone does
    *not* work here, since that lookup never consults it).
  - **macOS/Linux:** no auto-download — install the system `mpv` package
    (`brew install mpv` / `apt install libmpv2`); the loader (`find_library`
    via `DYLD_*`/`ldconfig`) finds it without any of this. A `%PATH%`-style
    bundle-and-inject doesn't translate to these platforms: their dynamic
    loaders read `DYLD_LIBRARY_PATH`/`LD_LIBRARY_PATH` at process *launch*,
    not at import time, so a runtime `os.environ` tweak is too late.
- **Missing libmpv doesn't break fman.** `import mpv` raises `OSError`
  immediately if the native library isn't found — and since `videoviewer.py`
  is imported unconditionally by `core/commands/opening.py`, an eager
  top-level `import mpv` would have broken *every* command on a machine
  without libmpv installed. The import (and, on Windows,
  `ensure_libmpv_on_path()`) is deferred to the moment a video is actually
  opened (`show_video_viewer`); if either fails, an alert explains the
  problem instead of the viewer (or fman) crashing. Browsing files and
  `is_video()` extension routing work regardless.
- **In the frozen (fbs/PyInstaller) build, `mpv` reaches the app only via
  `hidden_imports`.** The Core plugin ships as resource data
  (`src/main/resources/base/Plugins/Core` → `${freeze_dir}/Plugins/Core`), so
  PyInstaller never scans this file and never sees `import mpv` — exactly the
  situation `core/net.py`'s `requests` is in. Both are therefore listed in
  `src/build/settings/base.json`'s `hidden_imports`; drop `mpv` from that list
  and the packaged app raises `ModuleNotFoundError` on the first video.
  `copy_python_library('mpv', ...)` (the send2trash / python_localization
  route in `build_impl/windows.py`) is *not* usable here: it calls
  `import_module`, and `mpv.py` raises `OSError` at import time on a build
  machine without libmpv on `%PATH%`.
- **The native `libmpv` is not bundled.** On Windows `core/libmpv.py`
  downloads and caches `libmpv-2.dll` on first use (see its module docstring);
  macOS/Linux expect `mpv` from the system package manager.

## Why it works while the file list is hidden

Same mechanism as the text and image viewers — see
[`docs/views/TEXT_VIEWER.md`#why-it-works-while-the-file-list-is-hidden](TEXT_VIEWER.md#why-it-works-while-the-file-list-is-hidden).
The video viewer reuses the identical pane-mounting glue
(`core/textviewer_pane.py`), so the same explanation applies verbatim.

## Implementation

- `src/main/resources/base/Plugins/Core/core/videoviewer.py`:
  - `VIDEO_EXTENSIONS` / `is_video(url)` — the extension check that routes
    "View file" to this viewer (pure, unit tested).
  - `format_time(seconds)` — pure helper rendering `M:SS` or `H:MM:SS` for
    the time readout (unit tested).
  - `get_saved_volume()`/`save_volume(volume)`, `get_saved_mute()`/
    `save_mute(muted)` — thin wrappers over `core/settings.py`'s
    `get_setting`/`save_setting('Core Settings.json', ...)`, exactly the
    pattern `core/imageviewer_zoom.py`'s saved-scale functions use. `None`
    volume means nothing saved yet (mpv's own default, 100); mute defaults to
    `False`.
  - `PaneVideoView(QWidget)` — the viewer widget: a native child `QWidget`
    surface libmpv renders into (via its window handle, `wid=`), plus a
    `QLabel` time readout updated by a 250ms `QTimer` poll. Polling (rather
    than an mpv property-observer) is deliberate — observer callbacks fire on
    mpv's own thread, and touching a `QLabel` from there is unsafe.
    `keyPressEvent` mirrors `PaneImageView`'s (Ctrl+Shift+P opens its own
    palette, Escape/Enter/Backspace close, Tab/Backtab switch panes) with
    media controls (Space/Left/Right/Up/Down) instead of zoom, plus a
    `_bindable_commands()` lookup (see "Bindable commands" above and
    `core/key_bindings.py::command_for_key_event` below) checked before those
    hardcoded fallback keys, so a `Viewer Key Bindings.json` rebind always
    wins. On
    `destroyed` (fired by `close_view`'s `deleteLater()`), the mpv player is
    `terminate()`d — the one lifecycle hook shared pane-closing already
    triggers, so no shared code needed forking.
    - `start_playback` restores the saved volume/mute (if any) right after
      `self._player.play(path)`, before the 250ms timer starts.
    - `_adjust_volume`/`_reset_volume`/`_toggle_mute` each update
      `self._player`, persist via the wrappers above, and flash the new state
      through `_show_osd`, which calls mpv's own `show_text(text, ms)` — no
      Qt overlay widget, since there's no reliable way to composite one over
      the native `wid=`-embedded mpv surface.
    - A `ViewerNavigator(pane, 'video')` (from `core/viewer_navigation.py`,
      shared with the image/text viewers) supplies the Next/Previous-file
      actions, the same-type toggle, and their bindable pseudo-commands;
      `_open_palette` delegates to that module's `open_viewer_palette`. See the
      [image viewer](IMAGE_VIEWER.md#implementation) for the module's own
      description.
    - `_get_actions` names every row after the pseudo-command it runs
      (`video_toggle_pause`, `video_restart`, `video_mute`,
      `video_reset_volume`, `viewer_close`, plus the navigator's), which is
      what lets Shift+Enter on any of them rename it, add keywords, or bind a
      key — see
      [Changing key bindings from the palette](../COMMAND_PALETTE_KEYBINDINGS.md).
    - **`start_playback(mpv_module, path)` is separate from `__init__`, and
      must run only after the view is mounted into the pane and shown.**
      Creating the mpv player (which grabs `winId()`) and calling `.play()`
      *before* the widget is part of the visible layout embeds mpv into a
      surface with no real size/visibility yet — it renders as a
      permanently grey box even though audio (unaffected by the visual
      embed) plays fine. `_open_video_view` calls `mount_view` first, then
      defers `start_playback` one event-loop tick via
      `QTimer.singleShot(0, ...)` — the same technique `mount_view` already
      uses for `view.setFocus()`, for the same class of "widget isn't fully
      realized yet" timing issue.
  - `show_video_viewer(pane, url)` — deliberately *not*
    `@run_in_main_thread` (see "Playback backend" above for why); on
    Windows, calls `ensure_libmpv_on_path()` first, then lazily imports
    `mpv`, then hands off to `_open_video_view`.
  - `_open_video_view(pane, url, mpv_module)` — the actual
    `@run_in_main_thread` Qt work: mirrors `show_image_viewer`, mounting via
    `core/textviewer_pane.py`'s `begin_new_view`/`mount_view` before
    deferring `start_playback` as described above.
- `src/main/resources/base/Plugins/Core/core/libmpv.py` — Windows-only
  download/cache/verify of `libmpv-2.dll` (see "Playback backend" above).
  `cache_dir()` and `ensure_libmpv_on_path()` are the public surface; no Qt
  dependency, unit tested in isolation from the mpv/Qt-specific code.
- `src/main/resources/base/Plugins/Core/core/net.py` — `get_bytes(url)`, a
  small `urlopen`-with-`requests`-fallback HTTP fetch extracted out of
  `core/github.py` (plugin discovery/updates), which now delegates to it.
  Not used by `core/libmpv.py`: the libmpv download needs byte-level
  progress reporting (see "Playback backend" above), so it streams via
  `requests.get(..., stream=True)` directly instead — a genuinely different
  capability `get_bytes`'s small in-memory GitHub API fetches don't need.
- `src/main/resources/base/Plugins/Core/core/commands/opening.py` —
  `ViewFile.__call__` branches on `is_video(url)` (checked after
  `is_image(url)`, before the text fallback), calling `show_video_viewer`
  instead of `show_image_viewer`/`show_text_viewer` for video files; see
  [`docs/functions/view-file.md`](../functions/view-file.md).
- `src/main/resources/base/Plugins/Core/core/key_bindings.py` —
  `command_for_key_event(key_event, key_bindings, command_names)` generalizes
  `core/textviewer_zoom.py::zoom_delta_for`'s single-command shortcut lookup
  to an arbitrary set of viewer-only pseudo-commands: the first name in
  `command_names` whose configured shortcut matches, else `None`. Shared by
  all three viewers' `_bindable_commands()` (see their own docs for the
  image/text lists).
- `pyproject.toml` — `python-mpv==1.0.8`.
- Tests:
  - `core/tests/test_videoviewer.py` — `is_video()`'s extension matching
    (case-insensitive, non-video/no-extension rejected), `format_time()`'s
    formatting/clamping, and `get_saved_volume`/`save_volume`/
    `get_saved_mute`/`save_mute` round-tripping through a fake in-memory
    settings store (patching `core.videoviewer.get_setting`/`save_setting`),
    mirroring the image viewer's test style. No Qt, no mpv — pure-Python
    checks, importable even on a machine without libmpv installed.
  - `core/tests/test_key_bindings.py` — `command_for_key_event` matching a
    bound command, resolving correctly regardless of `command_names` order,
    and returning `None` on no match. No Qt-dependent mocking needed: it uses
    the real `QtKeyEvent`, same as `test_textviewer_zoom.py`.
  - `core/tests/test_libmpv.py` — `cache_dir()`'s path, the non-Windows
    no-op, cache-hit vs. cache-miss branching (mocking `submit_task`,
    asserting `%PATH%` gets the cache dir exactly once even across repeated
    calls), a failed/canceled download raising instead of proceeding as if
    libmpv were available, and `_DownloadLibmpv`'s SHA-256 mismatch raising
    before extraction ever runs. No network calls, no Qt.
  - `tools/clear_libmpv_cache.bat` — deletes
    `DATA_DIRECTORY/Local/libmpv/` so the next video opened re-downloads
    from scratch, for manually testing the download path.
  - The remaining Qt/mpv-specific behaviour (actual embedding via `wid=`,
    playback, key handling, Tab/focus-proxy switching, the palette dialog,
    the missing-libmpv alert) was verified interactively, not
    unit-tested — same approach the text and image viewers take (see
    [`docs/views/TEXT_VIEWER.md`](TEXT_VIEWER.md), Implementation section).
