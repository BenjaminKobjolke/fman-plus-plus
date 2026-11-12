# Recording demos

fman can record animated demos (GIF/MP4 + PNG stills) of its UI with the
[automated-application-screenshots](https://github.com/BenjaminKobjolke/automated-application-screenshots)
tool. The recorded demos are shown in the [README](../README.md#see-it-work).

Recording the feature tour end to end is six commands (see
[Recording checklist](#recording-checklist)); the rest of this document is what
you need when a step doesn't do what you scripted.

Everything that used to live in a folder of build scripts — joining the tour,
burning the captions, encoding the GIFs — is now the recording tool's
`--compose` flag, driven by the `compose` section of
`tools/create_media/fman.json`. This page covers what is specific to fman; the
generic half is in the tool's
[CONFIG.md](https://github.com/BenjaminKobjolke/automated-application-screenshots/blob/main/docs/CONFIG.md),
[DEMO_COOKBOOK.md](https://github.com/BenjaminKobjolke/automated-application-screenshots/blob/main/docs/DEMO_COOKBOOK.md)
and
[RECORDING_ENVIRONMENT.md](https://github.com/BenjaminKobjolke/automated-application-screenshots/blob/main/docs/RECORDING_ENVIRONMENT.md).

## How it works

In demo mode fman plays a scripted sequence of UI actions and reports events
over a socket so the tool can capture the window. The wiring:

- `src/main/python/fman/impl/demo_scripts.py` — the `DEMOS` registry, one
  `DemoScript` per recordable demo: the overview demo and the themes builder.
- `src/main/python/fman/impl/demo_scripts_features.py` — the `feature-*` clips,
  merged into `DEMOS` the same way as the tour chapters below.
- `src/main/python/fman/impl/demo_scripts_tour.py` — the `tour-*` chapters,
  merged into `DEMOS` by `demo_scripts.py`. Split out to keep both files
  under the project's 300-line limit.
- `src/main/python/fman/impl/demo.py` — the PyQt5 demo player that turns those
  scripts into key events.
- `src/main/python/fman/impl/application_context.py` — `run()` enters demo mode
  when `--automation-demo` is on the command line (`_run_demo()`), and skips the
  splash/tutorial and single-instance handoff so the recording is clean.
- `tools/create_media/fman.json` — the tool-side config. Two halves: `demos`
  (the 1920x1080 window size, formats, which `group` a demo belongs to, the tour
  captions, and `scale_to_window_size`) and `compose` (what gets built out of
  the recordings afterwards). The recorder's
  [`scale_to_window_size` setting](https://github.com/BenjaminKobjolke/automated-application-screenshots/blob/main/docs/CONFIG.md#scale_to_window_size-boolean-default-false-demo-mode-launch-only)
  caps desktop stills and video frames at the configured window dimensions.
- `tools/create_media/run_fman_demo.bat` — launcher the tool starts per run.
- `tools/create_media/demo_Theme_default.css` — Core font sizes at 1.5x, seeded
  into every demo profile except ids 8, 9, 10 and 21.
- `tools/create_media/demo_Theme.css` — larger font sizes for standalone clips,
  seeded for ids 8, 9, 10 and 21.
- `tools/demos_record.bat` — one command that drives recording **and**
  composing; every argument passes straight through to the tool.
- `tools/demos_build_tour.bat` — the join step on its own, for double-clicking:
  a one-line wrapper for `demos_record.bat --compose tour`. Recording does not
  compose, and with no argument `demos_record.bat` records everything and builds
  nothing — this is the second half.

The four artifacts the README shows are the four entries in `fman.json`'s
`compose` array, built with `--compose`:

| compose step | reads | writes |
|---|---|---|
| `tour` | every demo with `"group": "tour"`, in id order | `media/demos/tour/feature-tour.mp4` |
| `stills_gif` | the `themes` demo's PNGs | `media/demos/themes/themes.gif` |
| `mp4_gif` | every demo with `"group": "feature"` | `media/demos/features/<short>.gif` |
| `mp4_gif` | every demo with `"group": "plugin"` | `media/demos/plugins/<short>.gif` |

`<short>` is the demo name without its group prefix, so `feature-goto` writes
`goto.gif`. The plugin step carries its own tighter encoder settings — see
[DEMOS_PLUGINS.md](DEMOS_PLUGINS.md).

fman renders each `Screenshot` still itself with Qt and sends it in the
`screenshot` event as a base64 `png` field. The tool still grabs the window
region with pyautogui for GIF/MP4 frames. The `themes` and `dialogs` stills-only
demos therefore work on a locked or disconnected desktop when the tool supports
uploaded stills; an older tool ignores the field and captures the desktop as
before. `ScreenStill` steps are captured by the tool from the screen, so they
need an unlocked desktop.

### Panes and the demo profile

Demo 1 reads the committed `examples/left_pane` (images + a video) and
`examples/right_pane` (text/markdown). The tour chapters create, rename, move
and pack files, so `run_fman_demo.bat` gives every id ≥ 3 its own scratch
fixtures, wiped and re-seeded on each run:

| path | contents |
|------|----------|
| `D:\fman-demo\<id>-left` | both example folders merged — 11 images/video + 6 text files |
| `D:\fman-demo\<id>-right` | empty |
| `%TEMP%\fman-demo-profile` | the throwaway fman data directory |

The scratch folders are not in `%TEMP%` because that path holds the Windows
user name, and the Move, Copy and Pack prompts show the scratch path on camera.
Set `FMAN_DEMO_SCRATCH` to use another base folder. If the base cannot be
created, the launcher stops with an error instead of recording empty panes.

Two ids get extra seeding on top of that shared copy, because their feature
cannot be shown without it:

| id | extra |
|----|-------|
| 8 | `projects\alpha`, `projects\beta` and `reports` in the left folder, plus a 5-entry `Visited Paths.json` in the demo profile — see [Chapter 8 records a suggestion list](#chapter-8-records-a-suggestion-list---check-it) |
| 9 | `service.log` in the left folder, plus a background PowerShell appender that adds a line every 1.5 s for 60 s, so tail mode has something to follow |
| 10 | the MatrixRain plugin copied in from `%APPDATA%`, and the example text files in the *right* folder too — see [DEMOS_PLUGINS.md](DEMOS_PLUGINS.md) |
| 16 | the DemoAccount fake-account plugin in `Plugins\User` |

Every run sets `FMAN_DATA_DIRECTORY` to that profile and wipes its `Plugins`
folder. It also sets `PYTHON_KEYRING_BACKEND` to the null keyring, so recordings
start signed out and never read real account credentials. Recording against
your own profile would load your third-party plugins,
whose key bindings are prepended (so they beat Core's: `ArrowNavigation` takes
Left/Right, `fman-flatview` takes `Ctrl+F2`) and whose commands change what a
typed palette query resolves to — `compare`, for instance, stops meaning
`Compare directories`. It would also write viewer zoom and volume back into
your settings, so a second recording wouldn't match the first. Redirecting
`APPDATA` would isolate the same things, but that is also where `pip --user`
installs PyQt5 and fbs_runtime, hence fman's own override.

Two things are deliberately copied *in* from your real profile, because they
change how a recording looks rather than how it behaves:

- `Local\Settings.json` — your theme. Without it every demo records in the
  default Monokai. The `window_opacity` in that file has no effect: demo mode
  pins `DEMO_OPACITY` (`demo_scripts.py`) so every chapter starts at the same
  known value, whatever your profile or a previous take says. That value is
  fully opaque, because a translucent window makes the text hard to read on
  the website.
- `%APPDATA%\fman\Themes` — mirrored so a *custom* theme resolves instead of
  silently falling back to the default.

For the tour chapters (ids 3-7) the launcher sets
`"pane_location_bars_visible": false` in the demo profile's
`Local\Settings.json`; this hides the full folder path above each pane. Other
demos keep the path line, which reads `D:\fman-demo\…` and holds no user name.

Every demo gets one thing seeded that no profile of yours supplies:
`Plugins\User\DemoFont\Theme.css`. Demos use the 1920x1080 window and enable
the recorder's `scale_to_window_size` option, so scaled displays cannot make
their stills or frames larger than Full HD. The default font file scales Core
sizes by 1.5 for the stills. The tour chapters (ids 3-7) and the standalone
feature and plugin clips use `demo_Theme.css`: the tour is shown on the website
at about 1100 px, where the 1.5x font was too small to read, and
the 800 px feature GIFs need a 21pt app-wide font to read as
about 8.75pt after downscaling. Id 10's GIF ships at 360 px, where no font size
is readable, but a plugin clip that *does* hinge on text needs both the bump and
a wider encode - see [DEMOS_PLUGINS.md](DEMOS_PLUGINS.md). It is a user plugin, and `Theme` keeps CSS load
order, so it wins over `Plugins/Core/Theme.css` — but only by being **last**:
both consumers (`CSSEngine` for the hand-painted quicksearch item text, and
the generated Qt style sheet) resolve `*` against more specific selectors by
load order, not by specificity. Hence every selector that must not inherit the
app-wide font is restated *after* the `*` rule inside each file.

One thing it cannot reach: the inline filter's input (`FilterBar QLineEdit`,
`styles.qss`) stays 9pt — that selector is not in `Theme._CSS_TO_QSS`, so no
user Theme.css can express it. Neither clip uses the inline filter.

### Clearing the desktop

The recording tool minimizes every visible top-level window before it starts
the launcher (`"minimize_all"` in its config, on by default). Two separate
things make a leftover window fatal to a take: the recorder grabs screen
*pixels* of fman's window rect, so anything drawn over it is burned into every
frame; and while a script turns fman translucent (the overview's opacity
chapter, a theme with its own `opacity`), whatever sits *behind* fman
shows through it, putting that window's contents on camera without ever
covering fman.

fman used to do this itself, in `tools/create_media/minimize_all_windows.ps1`.
That script is **gone** — the tool now runs the same enumeration, ported from
it: visible, not iconic, has a title, class not one of the shell's own
(`Progman`, `WorkerW`, `Shell_TrayWnd`, …, or the screen goes black instead of
clear), then `ShowWindow(SW_MINIMIZE)` and a settle, because `ShowWindow`
returns while the shell is still animating.

Two things about that history are worth keeping:

- It replaced `(New-Object -ComObject Shell.Application).MinimizeAll()`, the
  Win+D shortcut, which *toggles* rather than minimizes and is ignored outright
  in some states. It reported success while leaving windows on screen, and the
  first plugin recording came back with the desktop's file names legible through
  fman's translucent frame. Do not go back to it.
- The tool's pass covers **its own console** too: it launches the launcher with
  `subprocess.Popen` and no `creationflags`, so `cmd /c` inherits the existing
  console rather than opening a new one, and a console is minimized like any
  other window. That is why fman no longer needs a pass of its own.

The tool logs how many windows it minimized. A zero on a take that came out
wrong is the tell. Nothing clears the desktop when you run
`run_fman_demo.bat` or fman by hand — close what is on screen yourself.

## Install (once)

Demo mode needs the app-side connector library. It is in the `demos` dependency
group of `pyproject.toml`, which is a default uv group, so every plain `uv sync`
installs it and routine app starts keep it installed. The release freeze
explicitly excludes it in `src/build/settings/base.json`. From the repo root:

    uv sync

This installs [automated-screenshot-connector](https://github.com/BenjaminKobjolke/automated-application-screenshots-python-connector)
from GitHub. To work on a local checkout of it instead:
`uv pip install -e ../automated-application-screenshots-python-connector`

The recording tool itself is a separate checkout and runs with
[uv](https://docs.astral.sh/uv/). Expected at
`../automated-application-screenshots` (edit `TOOL_DIR` in
`tools/demos_record.bat` if yours is elsewhere).

**Joining the tour needs [Node.js](https://nodejs.org) 18+.** The tour is
rendered with Remotion, so once per checkout:

    cd ..\automated-application-screenshots\composer
    npm install

Recording, the themes GIF and the feature GIFs need none of that — they are pure
Python, and **ffmpeg no longer has to be on `PATH`**: the tool uses the binary
that ships with its `imageio-ffmpeg` dependency.

**gifsicle** stays optional, and only the plugin GIFs use it (`"lossy"` in their
compose step). Without it on `PATH` the build prints a note and ships a larger
file.

**The interpreter matters.** fman's dependencies (PyQt5, fbs_runtime) and the
connector live in the project's `.venv`, and the launcher uses
`.venv\Scripts\python.exe` (`tools\find_build_python.bat`). Set `FMAN_PYTHON`
only to override it. (The launcher also drops the tool's own `uv` virtualenv
from `PATH`.)

## Recording checklist

1. **Close every always-on-top desktop widget** (clock/system-monitor gadgets,
   notification toasts, anything pinned above other windows). Ordinary windows
   are handled for you — the tool minimizes them before launching fman (see
   above) — but a window pinned above others survives that, and the capture is a
   screen region, so
   whatever is drawn over fman is burned into every frame and no setting in the
   tool can exclude it. The same goes for anything left *behind* fman: it
   shows through while a script turns the window translucent.
2. **Check libmpv is cached** at
   `%TEMP%\fman-demo-profile\Local\libmpv\libmpv-2.dll` — the launcher copies it
   from your real profile. Without it the first video view downloads ~100 MB
   behind a progress dialog, on camera.
3. **Preview any script you changed** (see
   [Preview a demo](#preview-a-demo-without-the-tool)) and check its side
   effects; don't burn a recording on an unproven script.
4. **Record the chapters one at a time** so a misfire costs one clip, not five:

       tools\demos_record.bat --demo 3
       tools\demos_record.bat --demo 4
       tools\demos_record.bat --demo 5
       tools\demos_record.bat --demo 6
       tools\demos_record.bat --demo 7

5. **Join them:** `tools\demos_build_tour.bat` (same thing as
   `tools\demos_record.bat --compose tour`) → `media/demos/tour/feature-tour.mp4`.
6. **Watch the result** before committing. The build prints the size; the last
   ffmpeg-joined run was 2:32 and 2.3 MB.
7. **Re-upload it to GitHub and update the README** (see
   [Publishing the tour](#publishing-the-tour)). Committing the new MP4 is not
   enough — the README plays a *copy* hosted by GitHub.

Everything else is one command each, and each records *and* builds:

| what | command |
|---|---|
| the whole lot | `tools\demos_record.bat --demo all --compose` |
| the themes GIF | `tools\demos_record.bat --demo 2 --compose themes` |
| the feature GIFs | `tools\demos_record.bat --demo 8`, then `--demo 9`, then `--demo 21`, then `--compose features` (one demo per run — a second `--demo` overrides the first) |
| the plugin GIF | `tools\demos_record.bat --demo 10 --compose plugins` |
| rebuild without re-recording | `tools\demos_record.bat --compose features` |
| what can this config even do? | `tools\demos_record.bat --list` |

`--compose` on its own builds all four artifacts; with an argument it matches a
step's output path or its type. A failed recording stops the build rather than
composing stale inputs.

## What ships

- **1 `overview`** — short; the stills in the README feature grid
  (both panes, internal image viewer, inline filter, select-all). The only
  demo whose PNGs are committed - the themes demo's are an intermediate.
- **2 `themes`** — one still per bundled theme, joined into the README's
  `media/demos/themes/themes.gif`. Records no video at all.
- **11 `dialogs`** — stills of the copy prompt, overwrite question and delete
  confirmation with and without the title bar, plus the permanent-delete
  (Shift+Delete) confirmation. This exists so the automated
  screenshot check can judge dialog changes. Its stills are gitignored
  (`media/demos/dialogs/`); each check records them fresh.
- **12 `links`** — stills of a junction and shortcut in the panes, the palette's
  *Edit link target* entry and its target prompt (cancelled). Exists so the
  screenshot check can judge link features.
- **13 `context-menu`** — stills of the palette searching *Run as administrator*
  and of the file context menu (the still shows the menu alone). It never presses
  Return, which would raise a UAC prompt. Exists so the screenshot check can judge
  palette entries and context-menu items.
- **14 `command-palette`** — stills of palette searches, currently *Go to network*
  and the network view it opens (Windows). Exists so the screenshot check can judge
  new palette entries. A change that adds a palette command should add a `TypeText`
  query plus a `Screenshot` still here, so its check has something to judge.
- **15 `listing`** — stills of both panes without and with file age shading on
  backdated scratch files. Exists so the screenshot check can judge changes to how
  the file list looks (shading, colors, columns), instead of the tour chapters that
  record no stills. It also takes stills with the pane location bars hidden and
  shown again; the launcher starts it with them visible whatever the copied
  settings say. Its stills are gitignored (`media/demos/listing/`). A change to the
  file list's look should add a `Screenshot` here.
- **17 `ftp-overwrite`** — records an FTP folder upload with an existing file,
  showing the progress window before the overwrite question, hidden while the
  question is open, and back after answering. It needs `FMAN_FTPClient` installed
  and seeds a loopback fake FTP server with slow listings; its stills are
  gitignored (`media/demos/ftp-overwrite/`).
- **18 `single-instance`** — launches a separate `--new-instance` window, then
  starts fman normally and shows that the original window receives the forwarded
  folder. Its stills are `single-instance-primary`,
  `single-instance-new-window` and `single-instance-forwarded-to-original`. It
  records stills only and exists so the screenshot check can judge
  single-instance and `--new-instance` changes.
- **19 `transfer-failure`** — copies a folder in which `run_fman_demo.bat` holds
  one file open, so only that file's copy fails. Stills show the end-of-copy
  retry question, the question again after a failed retry, and the file that did
  copy. It exists so the screenshot check can judge copy and move failure
  handling; stills are gitignored (`media/demos/transfer-failure/`).
- **20 `dialogs-after-video`** — opens and closes the seeded in-pane video before
  taking stills of the playing video, Delete confirmation, command palette, copy
  prompt and overwrite question. It exists so the screenshot check can judge
  in-window dialog changes after the video viewer. The demo posts Qt key events,
  so real mouse and operating-system input remains a by-hand check; stills are
  gitignored (`media/demos/dialogs-after-video/`).
- **22 `folder-tree`** — opens Toggle folder tree on a scratch folder with seeded
  subfolders and takes one still with the current folder expanded (rows, icons,
  arrows and indentation). It exists so the screenshot check can judge folder
  tree changes. The tree starts at the drive root, so the still also shows the
  scratch drive's top-level folders. Once the parents load, the tree centers the
  current folder so the still shows `22-left` with its siblings and its
  `archive`, `projects` and `reports` children; stills are gitignored
  (`media/demos/folder-tree/`). A change to the folder tree's look should add a
  `Screenshot` here.

Screenshot checks should not record demo 1: until the screenshot tool honors
`--output` for demos (#15344), its stills overwrite the committed README images.
- **3–7, the `tour-*` chapters** — the README's feature tour:

  | id | name | shows | measured |
  |----|------|-------|----------|
  | 3 | `tour-a-panes` | select, copy across panes, type-to-filter, sort | 302 frames, 30.2 s |
  | 4 | `tour-b-organize` | `F7` new folder, `F6` move, `Shift+F6` rename | 267 frames, 26.7 s |
  | 5 | `tour-c-viewers` | image viewer + zoom + next file, text viewer + edit/save | 328 frames, 32.8 s |
  | 6 | `tour-d-video` | video playing in the pane, and previewing into the other one | 276 frames, 27.6 s |
  | 7 | `tour-e-archives` | pack, browse inside the zip, copy out, fuzzy palette | 354 frames, 35.4 s |

- **8, 9 and 21, the `feature-*` clips** - standalone, NOT part of the joined tour.
  They carry `"group": "feature"`, which the third `compose` step turns into the
  committed GIFs the README's feature index shows
  (`media/demos/features/goto.gif`, `tail.gif`, `commands.gif`):

  | id | name | shows | measured |
  |----|------|-------|----------|
  | 8 | `feature-goto` | `Ctrl+P` Go to: fuzzy jump, tab-complete, Enter | 101 frames, 20.2 s |
  | 9 | `feature-tail` | tail mode following a log while it grows | 106 frames, 21.2 s |
  | 21 | `feature-commands` | `Ctrl+Shift+P` palette: new folder, rename, view, delete, select all, deselect, copy | 249 frames, 49.8 s |

  They also record with a bigger font than everything else — see the demo
  profile section above.

  They record at **`fps: 5`**, not 10. Capture could not keep up with an
  animated theme behind the window (~4.8 fps measured), and the exporter writes
  the frames it got at whatever fps the config names - so 10 produced a clip
  that played at double speed. Match the fps to what the machine can capture,
  or the demo lies about how fast it was.

  What keeps them out of the hero video is their **`group`**, not their name:
  the tour step joins every demo with `"group": "tour"`. The `tour-`/`feature-`/
  `plugin-` name prefixes now only decide the output filename (`{short}` strips
  the group prefix), so the two must agree — a `feature-*` demo put in the tour
  group would be joined into the tour and still be written as `goto.gif`.

- **10, the `plugin-*` clip** - films a *third-party plugin* rather than fman,
  for the README's plugin list and the plugin's own README. It has its own
  prerequisite (the plugin must be installed), its own seeding rule and its own
  encoder settings, all documented in
  [DEMOS_PLUGINS.md](DEMOS_PLUGINS.md) rather than repeated here:

  | id | name | shows |
  |----|------|-------|
  | 10 | `plugin-matrix-rain` | MatrixRain in one pane, then translucent, then both panes |

### Chapter 8 records a suggestion list - check it

Go to (`Ctrl+P`) suggests **real folders from the recording machine**, so this
is the one chapter that can put private directory names on camera.
`SuggestLocations` (`core/suggest_locations.py`) draws them from two places:

| source | when | what it would show |
|--------|------|--------------------|
| `_get_default_paths()` | `Visited Paths.json` holds **2 or fewer** entries | every non-hidden subdir of your home directory, plus the non-empty dirs in `C:\` |
| `find_folders_starting_with()` | the typed query is **longer than 2 chars** | up to 5 folders from the Windows Search index, from anywhere on the disk |
| `_with_well_known_dirs()` | **always** | home, Desktop, Documents, Downloads |

`run_fman_demo.bat` closes the first two for id 8: it seeds a 5-entry
`Visited Paths.json` pointing only at that run scratch tree (so the fallback
never fires), and the script never types more than two characters (so the
index is never queried). Keep both properties if you edit the chapter - and
watch the take before publishing it.

The third source **cannot be closed** - the everyday four are offered
unconditionally. They are safe to record only because `SuggestLocations`
`_filter_matching` sets `use_tilde` whenever the query does not already start
inside your home directory, so they render as `~`, `~\Desktop`, `~\Documents`,
`~\Downloads` - never `C:\Users\<name>\...`. That tilde-shortening is now the
only thing keeping the account name off camera in chapter 8: if a change ever
makes GoTo show these rows unshortened, the chapter has to be re-checked
before publishing.

The chapters exist because of hard limits in the recorder, not taste:

| limit | value | consequence |
|-------|-------|-------------|
| frames held in RAM | ~6 MB each at 1920x1080, and the MP4 export copies them all again as numpy arrays | ~60 MB per second at 10 fps — a single 2.5-minute take needs gigabytes |
| `DEMO_CAP_S` | 300 s | a longer demo is aborted |
| `EVENT_TIMEOUT_S` | 60 s | 60 s with no `demo_started`/`screenshot`/`demo_ended` aborts the run. A chapter under a minute is covered by `demo_started` alone; a longer one needs `Screenshot` steps as heartbeats |
| `WINDOW_TIMEOUT_S` | 30 s | fman must show its window within 30 s of launch |

Output lands in `media/demos/<name>/` (see `output_dir` in
`tools/create_media/fman.json`): `demo.mp4`, plus `demo.gif` and one PNG per
`Screenshot` step if the demo asks for them. The tour chapters and the
standalone clips are `mp4` only — a 2.5-minute GIF would be tens of
megabytes for a worse picture, and the GIFs are encoded from the mp4
afterwards (a 64-colour palette at 800 px keeps each `feature-*` one under half
a megabyte; the `plugin-*` clips need tighter settings, see
[DEMOS_PLUGINS.md](DEMOS_PLUGINS.md)).

`--compose tour` renders the chapters into one MP4 with **Remotion**, holding
each chapter's `caption` over its first 5 s between an optional intro and outro
card. Everything it needs is in `fman.json`: the chapter order is every demo with
`"group": "tour"` sorted by id, and the caption text is that demo's `caption`
field — one place, next to the demo it belongs to. The tool refuses to build a
tour whose chapters have no caption, so a new chapter cannot ship untitled.

Two things the old ffmpeg join had to do by hand come free: captions no longer
need escaping (ffmpeg's filter syntax eats commas, colons and the Windows drive
colon, so the text had to go through a temp file), and clips recorded in
different sessions no longer have to be rescaled to a common size before
`concat` will accept them — the capture is the window *including* its frame
(1284x847 last time) and can differ by a pixel between takes.

Captions are also per-language ready: a `captions` object on a chapter
(`{"de": "..."}`) is used when that language is recorded, falling back to
`caption`. fman records no languages today, so nothing uses it yet.

Only the joined MP4 is committed — the per-chapter `media/demos/tour-*/` folders
are regenerable intermediates and gitignored. The same holds for
`media/demos/feature-*/` and `media/demos/plugin-*/`: only the encoded GIFs under
`media/demos/features/` and `media/demos/plugins/` are committed.

### Size budgets

Any compose step can state how big its artifact may be and which settings the
tool may trade away to get there:

```json
{"type": "mp4_gif", "group": "feature", "output": "demos/features/{short}.gif",
 "fps": 5, "width": 800, "colors": 64,
 "max_size": "2MB", "fit": ["colors", "fps"]}
```

`fit` lists the knobs the search may move, in the order it should spend them;
anything left out is a constraint, so `width` above stays at 800 whatever
happens. At most three encodes run, the first with exactly the settings you
wrote, and what is kept is the largest attempt that fits. fman's steps carry no
budget today — the measured settings already land where they should — but this
is the mechanism to reach for when a clip grows past what a README should carry.
Full rules: the tool's
[CONFIG.md](https://github.com/BenjaminKobjolke/automated-application-screenshots/blob/main/docs/CONFIG.md).

### Publishing the tour

The README plays the tour inline. GitHub only renders a player for a bare
`https://github.com/user-attachments/assets/<uuid>` URL on its own line — not
for a repo-relative path, not for a `<video>` tag. That URL points at a copy
GitHub stores when the file is uploaded through its editor, so **the committed
`media/demos/tour/feature-tour.mp4` and the video the README plays are two
separate files**. Rebuilding the MP4 changes nothing on the README page until
it is re-uploaded.

Upload from the CLI with the third-party `gh` extension (GitHub has no official
API for this endpoint):

    gh extension install drogers0/gh-image   # once
    gh image media/demos/tour/feature-tour.mp4 --repo BenjaminKobjolke/fman

It prints the new attachment URL; replace the old one under `## Demo` in the
README with it.

### The themes demo

Demo 2 is the only one whose steps are **built at run time**: `_run_demo`
passes `list_themes(bundled_theme_dirs)` to `build_themes_script`
(`demo_scripts.py`), which emits `Select theme` → `Screenshot(<name>)` per
theme. Add `Themes/Foo.json` and Foo is in the next recording — no edit to
`demo_scripts.py` or `fman.json`.

Three things make it look nothing like the other demos:

| choice | why |
|--------|-----|
| `"formats": []` in `fman.json` | the tool then writes only the PNG stills, so the command palette it uses to switch themes never lands in the GIF — and the frames it holds in RAM are thrown away |
| `"fps": 2` | When the tool captures the still itself (older tool), `Recorder.request_still` saves the *next captured* frame, so at 2 fps a still lands within 0.5 s of the event — inside the 1.2 s the script keeps the palette closed afterwards. With uploaded stills, the image is the window at the event. |
| **bundled** themes only | `theme_dirs` also holds the demo profile's `Themes`, which `run_fman_demo.bat` mirrors from `%APPDATA%` — so a repo asset would otherwise carry your private themes. Hence `bundled_theme_dirs` |

The `stills_gif` compose step then joins `media/demos/themes/*.png` in name
order (the order `list_themes` returns), holding each for its `hold` seconds —
keep that in step with `THEME_HOLD_S` in `demo_scripts.py`, which is how long
the recording itself dwells on a theme. It reads no theme list of its own: the
stills *are* the list. The tool deletes a demo's stills before re-recording it,
so a theme you removed cannot linger in the GIF.

The one thing to check by eye: `Command(name)` types the theme's full name
into the quicksearch, which matches with `contains_chars`, so a short name is
a subsequence of a longer one (`Dark` also matches `Gruvbox Dark`). Ties break
by sorted order, which today always favours the exact name — but a future
theme sorting *before* one whose name it contains (`Ayu Dark` before `Dark`)
would steal the query and write the wrong picture under the right file name.

## Preview a demo without the tool

Fastest way to iterate on pacing — plays visually, records nothing, quits
itself:

    set PYTHONPATH=src\main\python
    set FMAN_DATA_DIRECTORY=%TEMP%\fman-demo-profile
    python src\main\python\fman\main.py --automation-demo 1 examples\left_pane examples\right_pane

For a tour chapter, pass its scratch folders `D:\fman-demo\<id>-left` and `-right` instead (create them the way
`run_fman_demo.bat` does, or just run the chapter through the recorder once so
they exist).

**Check a chapter without watching it.** A preview leaves evidence: the files it
created, moved or renamed in the scratch folders, and the settings it persisted
in `%TEMP%\fman-demo-profile\Plugins\User\Settings\`. That is enough to prove
every risky step landed:

| chapter | proof it worked |
|---------|-----------------|
| 3 `tour-a-panes` | the right folder holds all 17 copies |
| 4 `tour-b-organize` | `documents/` exists and contains `history.txt` (renamed from `changelog.txt`) |
| 5 `tour-c-viewers` | `changelog.txt` ends with `Edited in fman` |
| 6 `tour-d-video` | `Core Settings (Windows).json` has `video_viewer_volume` — written only from the video viewer's own key handler, so it proves the viewer had keyboard focus |
| 7 `tour-e-archives` | `images.zip` in the left folder holds three JPEGs, and the right folder holds the one copied back out |
| 8 `feature-goto` | the left pane ends on `projects\alpha` — and `Visited Paths.json` in the demo profile lists only `D:\fman-demo\8-*` paths |
| 9 `feature-tail` | `service.log` is longer than the 12 seeded lines (the appender adds ~40 more over a minute) |
| 10 `plugin-matrix-rain` | `Matrix Rain (Windows).json` in the demo profile's `Plugins\User\Settings` holds `"transparency": 70` - which proves the palette query resolved, the prompt took the typed value, and the rain re-mounted |

**Estimate a script's length** without running it. The connector does the
arithmetic, start delay and end hold included:

    set PYTHONPATH=src\main\python
    python -c "from PyQt5.QtWidgets import QApplication; QApplication([]); from fman.impl.demo_scripts import DEMOS; from automated_screenshot_connector import estimated_duration; [print(s.name, round(estimated_duration(s), 1), 's') for s in DEMOS.values()]"

Compare the result against the recorder's 300 s cap, and eyeball the gaps
against its 60 s no-event timeout.

## Writing a demo

### The steps

All from `automated_screenshot_connector`; `flatten()` expands them into timed
atomic actions, and the delay attached to each action elapses **before** it runs.

| step | expands to | notes |
|------|-----------|-------|
| `Pause(seconds)` | one no-op wait | the only way to give the UI time |
| `PressKey(chord)` | one key press+release after 60 ms | must be a single Qt chord (`'Ctrl+Shift+P'`, `'Down'`, `'Ins'`, `'Alt+F5'`) |
| `TypeText(text)` | one press+release per char, 60 ms apart, carrying the char as text | drives the inline filter and any focused `QLineEdit` |
| `Command(line)` | `TypeText(line)` + Return | **does not open the palette** — precede it with `PressKey('Ctrl+Shift+P')` |
| `Screenshot(name)` | a `screenshot` event with fman's rendered PNG after 400 ms of settle | writes `media/demos/<demo>/<name>.png` |

Player constants live in `demo.py`: `START_DELAY_MS = 500` before the first
action, `END_HOLD_MS = 1000` after the last one.

Events are posted to `QApplication.focusWidget()`, which is why they reach modal
dialogs and viewers as well as the file list. An unparsable chord is rejected
when the player is constructed, so a typo fails before the window is even
captured rather than minutes into a recording.

`TypeText` cannot carry a newline in fman — the library expands `'\n'` into a
plain character event, not a Return. Use `PressKey('Return')`.

### Pane order

`core.Name.get_sort_value` sorts directories first, then case-insensitively and
naturally. The seeded scratch folder is therefore always:

| row | file | row | file |
|-----|------|-----|------|
| 0 | `changelog.txt` | 9 | `dummy_6.jpg` |
| 1 | `config.json` | 10 | `dummy_7.jpg` |
| 2 | `data.csv` | 11 | `dummy_8.jpg` |
| 3 | `dummy.mp4` | 12 | `dummy_9.jpg` |
| 4 | `dummy_1.jpg` | 13 | `dummy_10.jpg` |
| 5 | `dummy_2.jpg` | 14 | `notes.md` |
| 6 | `dummy_3.jpg` | 15 | `readme.md` |
| 7 | `dummy_4.jpg` | 16 | `todo.txt` |
| 8 | `dummy_5.jpg` | | |

`dummy.mp4` precedes `dummy_1.jpg` because `.` sorts before `_`, and
`dummy_10.jpg` sorts after `dummy_9.jpg` because the comparison is natural, not
lexicographic. The cursor starts on row 0, so every `Down` count in a script is
written against this table — re-check them if the fixtures ever change.

**Ids 8 and 9 do not match that table.** Their extra fixtures shift every row:
demo 8 adds `projects` and `reports`, which sort *before* every file because
directories sort first, and demo 9 adds `service.log` between `readme.md` and
`todo.txt`. Both scripts therefore avoid `Down` counts entirely — demo 9 uses
`End` then `Up` to land on the log, and demo 8 navigates by typing. Do the
same in any new clip that seeds extra files, or recount against the real
listing.

### Palette queries

The global palette (`Ctrl+Shift+P`) matches in three tiers —
word-prefixes, then contained characters, then contained characters in any
order — takes each command's **first** matching alias, and sorts each tier by
title length, so the shortest matching command title wins. Verify a new query
against `core/commands/palette.py` rather than guessing:

| query | resolves to | rival it beats |
|-------|-------------|----------------|
| `view file` | View file | `View file in other pane` |
| `view in other` | View file in other pane | — |
| `comp dir` | Compare directories | `Compare files` (a third-party command, absent from the demo profile but still a bad habit) |
| ~~`compare`~~ | ambiguous | picks `Compare files` when it exists |
| ~~`cd`~~ | **Move cursor down** | shorter title wins — not what you meant |
| ~~`cmp`~~ | **Compress...** | same trap |

A **viewer's own palette** (also `Ctrl+Shift+P`, handled inside the viewer
before the global one can see it) is simpler: single-tier character matching,
no sorting, first match in the viewer's action order wins. Verified queries:

| viewer | queries |
|--------|---------|
| image | `next`, `fit`, `zoom in`, `actual` |
| text (viewing) | `edit`, `exit`, `next` |
| text (editing) | `save`, `exit`, `revert` |
| video | `play`, `mute`, `restart`, `next`, `exit` |

### Dialogs and prompts

| command | what opens | prefill | confirm |
|---------|-----------|---------|---------|
| `F5` copy / `F6` move | a prompt | the other pane's path — **fully selected** for a multi-file selection, stem-only for a single file | Return. A bare name (no path) is resolved against the **source** pane |
| `F7` create folder | a prompt | the stem of the file under the cursor, fully selected | Return; the cursor is then placed on the new folder |
| `Shift+F6` rename | an **inline editor in the file list**, not a dialog | the stem, extension kept | Return. A path is rejected with an alert — type a bare name |
| `Alt+F5` pack | a prompt | `<other pane>\<name>.zip` with only the stem selected — press `Ctrl+A` first if you want to replace the whole path | Return |
| viewer *Save file* | **nothing** — writes straight to disk | — | — (*Save file as…* would prompt; avoid it) |
| overwrite conflict | a message box defaulting to Yes | — | Return. Better: script the demo so no conflict can happen |

A prompt selects its prefilled text only on its **second** paint, so wait
≥1.6 s after opening one before typing into it.

### Traps that cost a recording

- **A pane does not re-list itself** after a command creates a file in it. Press
  `Ctrl+R` (reload) before filtering for something the demo just made — this is
  why chapter 7 reloads after packing and chapter 3 reloads after copying.
  Without it the filter matches nothing, the cursor stays where it was, and
  every following step acts on the wrong file.
- **`Return` on a `.jpg`/`.mp4` in the file list launches the Windows default
  application** over your recording. Only press it on a directory, on a `.zip`
  (which fman rewrites into "open directory"), or inside a dialog.
- **Escape does not close the text viewer in edit mode** — use the viewer
  palette's `exit`.
- **Typing goes to whatever has focus.** If a prompt or progress dialog is still
  up, the rest of the script types into it and silently does nothing.

Pace for viewers: ~0.6–1.2 s after each result, longer after a copy or a video
start, and end with a `Pause(1.0)` so the recording doesn't cut off abruptly.

## Add a new demo

1. Add a `DemoScript` to `DEMOS` in
   `src/main/python/fman/impl/demo_scripts.py` with a new `id` and `name`.
   Verify chords against
   `src/main/resources/base/Plugins/Core/Key Bindings (Windows).json` and
   palette queries as described above.
2. Add a matching entry to the `demos` array in `tools/create_media/fman.json`
   (`id`, `name`, `fps`, `width`, `height`, `formats`). Ids ≥ 3 automatically
   get the scratch fixture folders. A stills-only demo like `themes` sets
   `"formats": []`.
   Use the `OpenContextMenu` step for demos that need the file context menu.
   A demo intended for visual checks should include `Screenshot` steps for each
   UI state those checks need to judge.
   Palette commands should add their query and still to demo 14 instead of a new
   demo.
   A feature demo that needs a signed-in fman account goes into demo 16, which
   uses the seeded fake account.
3. **Set its `group`**, which is what decides where it ends up — the name
   prefix only shapes the filename:

   | group | name it | ends up in |
   |---|---|---|
   | `"tour"` | `tour-<letter>-<topic>` | the hero video; **also needs a `caption`**, or the build refuses to run |
   | `"feature"` | `feature-<topic>` | `media/demos/features/<topic>.gif` |
   | `"plugin"` | `plugin-<name>` | `media/demos/plugins/<name>.gif`, see [DEMOS_PLUGINS.md](DEMOS_PLUGINS.md) |
   | *(none)* | anything | nothing is built from it automatically |

   No group means no compose step picks it up — which is right for a demo like
   `overview`, whose stills are used directly.
4. A tour chapter's script goes in `demo_scripts_tour.py` rather than
   `demo_scripts.py`, to keep both under the project's 300-line limit.
5. Every demo receives `demo_Theme_default.css`. For a standalone `feature-*`
   or `plugin-*` clip, choose `demo_Theme.css` instead by adding its id to the
   override lines in `run_fman_demo.bat`. The compose step picks up every demo
   in the group, and `{short}` names the output.
6. Preview it, check its side effects, then record and build:
   `tools\demos_record.bat --demo <id> --compose`.

## Troubleshooting

| symptom | cause | fix |
|---------|-------|-----|
| `ModuleNotFoundError: fbs_runtime` | wrong interpreter — the deps are in one interpreter's user site-packages | set `FMAN_PYTHON` to that `python.exe` |
| the demo runs but nothing after step N takes effect | a dialog still had focus, or a prompt was typed into before it selected its prefill | longer `Pause` before typing; check the dialog table above |
| a filter finds nothing right after the demo created a file | the pane hasn't re-listed | `PressKey('Ctrl+R')` before filtering |
| a photo viewer or media player opens mid-recording | `Return` was pressed on a file the cursor happened to be on | fix the cursor position; never press Return on a non-directory, non-`.zip` |
| the palette runs the wrong command | a shorter command title matched the query first | lengthen the query; see the table above |
| the text in a `feature-*` or `plugin-*` GIF is too small to read | it uses the default demo font CSS instead of the larger standalone variant | add its id to the `demo_Theme.css` override lines in `run_fman_demo.bat` and re-record |
| a clock/monitor overlay is visible in every frame | an always-on-top desktop widget | close it and re-record; the capture is a screen region |
| file names or window contents show faintly *through* fman | a window was left behind fman while the script had turned it translucent | check the minimize count the tool logs — a zero on a bad take is the tell; a window pinned always-on-top survives the minimize and has to be closed by hand |
| a video demo records a download dialog | libmpv isn't cached in the demo profile | copy `libmpv-2.dll` into `%TEMP%\fman-demo-profile\Local\libmpv\` |
| `Demo exceeded 300s cap` | one script is too long | split it into chapters |
| `No demo event for 60s` | a long stretch with no `Screenshot` step | add `Screenshot` heartbeats or shorten the chapter |
| the recording is huge or the machine swaps | frames are all held in RAM | shorter chapters, or a lower `fps` in `fman.json` |
| the clip plays too fast (a 20 s demo lasts 10 s) | capture couldn't hit the configured `fps` — an animated theme behind the window is enough — and the exporter writes the frames it got at the configured rate | lower the demo's `fps` in `fman.json` to what the machine actually captures (frames ÷ scripted seconds), then re-record. The GIF's own `fps` is a separate knob in its compose step |
| a `verify` check fails a run that looked fine | the demo played but a step didn't land — a dialog stole focus, a viewer never got it | check the evidence table under [Preview a demo](#preview-a-demo-without-the-tool); the failing check names the file it wanted |
| `--compose tour` says a clip is missing | that chapter wasn't recorded | record it; the message names the exact command |
| `--compose tour` says Remotion is not installed | `npm install` was never run in the tool's `composer/` | run it once, see [Install](#install-once) |
| `--compose` refuses to start, naming a chapter with no caption | a `"group": "tour"` demo has no `caption` in `fman.json` | add it; an untitled chapter cannot ship |
| a compose step builds nothing and says the group matches no demo | the demo's `group` is missing or misspelled | fix it in `fman.json`; `--list` shows every demo's group |
| a theme is missing from the themes GIF | its still was never written — the typed name matched another theme first | lengthen or rename; see [The themes demo](#the-themes-demo) |
| a still shows the wrong theme | same cause, but the file name says otherwise | as above; the file count alone won't catch it |

Full step reference: the connector repo's `docs/WRITING_DEMOS.md`; full
app-side contract: the tool repo's `docs/AUTOMATION_INTERFACE.md`.
