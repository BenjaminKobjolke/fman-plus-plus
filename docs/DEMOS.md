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
  `DemoScript` per recordable demo: the overview demo, the `feature-*` clips,
  and the themes builder.
- `src/main/python/fman/impl/demo_scripts_tour.py` — the `tour-*` chapters,
  merged into `DEMOS` by `demo_scripts.py`. Split out to keep both files
  under the project's 300-line limit.
- `src/main/python/fman/impl/demo.py` — the PyQt5 demo player that turns those
  scripts into key events.
- `src/main/python/fman/impl/application_context.py` — `run()` enters demo mode
  when `--automation-demo` is on the command line (`_run_demo()`), and skips the
  splash/tutorial and single-instance handoff so the recording is clean.
- `tools/create_media/fman.json` — the tool-side config. Two halves: `demos`
  (window size, formats, which `group` a demo belongs to, the tour captions) and
  `compose` (what gets built out of the recordings afterwards).
- `tools/create_media/run_fman_demo.bat` — launcher the tool starts per run.
- `tools/create_media/demo_Theme.css` — font sizes for the standalone clips,
  seeded into the demo profile by that launcher for ids 8, 9 and 10 only.
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

fman itself never captures or encodes anything. It only posts key events and
sends `demo_started` / `screenshot` / `demo_ended` over a socket; the tool grabs
the window region with pyautogui and writes the GIF/MP4.

### Panes and the demo profile

Demo 1 reads the committed `examples/left_pane` (images + a video) and
`examples/right_pane` (text/markdown). The tour chapters create, rename, move
and pack files, so `run_fman_demo.bat` gives every id ≥ 3 its own scratch
fixtures, wiped and re-seeded on each run:

| path | contents |
|------|----------|
| `%TEMP%\fman-demo-<id>-left` | both example folders merged — 11 images/video + 6 text files |
| `%TEMP%\fman-demo-<id>-right` | empty |
| `%TEMP%\fman-demo-profile` | the throwaway fman data directory |

Two ids get extra seeding on top of that shared copy, because their feature
cannot be shown without it:

| id | extra |
|----|-------|
| 8 | `projects\alpha`, `projects\beta` and `reports` in the left folder, plus a 5-entry `Visited Paths.json` in the demo profile — see [Chapter 8 records a suggestion list](#chapter-8-records-a-suggestion-list---check-it) |
| 9 | `service.log` in the left folder, plus a background PowerShell appender that adds a line every 1.5 s for 60 s, so tail mode has something to follow |
| 10 | the MatrixRain plugin copied in from `%APPDATA%`, and the example text files in the *right* folder too — see [DEMOS_PLUGINS.md](DEMOS_PLUGINS.md) |

Every run sets `FMAN_DATA_DIRECTORY` to that profile and wipes its `Plugins`
folder. Recording against your own profile would load your third-party plugins,
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
  known value, whatever your profile or a previous take says.
- `%APPDATA%\fman\Themes` — mirrored so a *custom* theme resolves instead of
  silently falling back to the default.

Ids 8, 9 and 10 get one thing seeded that no profile of yours supplies: a
`Plugins\User\DemoFont\Theme.css` copied from
`tools/create_media/demo_Theme.css`. Their GIFs are encoded narrower than the
1280 px capture - 800 px for the `feature-*` ones - so Core's 9pt lands at
~5.6pt in the README; the file bumps the app-wide `*` font to 14pt, which reads
as ~8.75pt after the downscale. Id 10 is seeded the same way as insurance
rather than necessity: its GIF ships at 360 px, where no font size is readable,
but a plugin clip that *does* hinge on text needs both the bump and a wider
encode - see [DEMOS_PLUGINS.md](DEMOS_PLUGINS.md). It is a user plugin, and `Theme` keeps CSS load
order, so it wins over `Plugins/Core/Theme.css` — but only by being **last**:
both consumers (`CSSEngine` for the hand-painted quicksearch item text, and
the generated Qt style sheet) resolve `*` against more specific selectors by
load order, not by specificity. Hence every selector that must not inherit the
14pt is restated *after* the `*` rule inside that file. The tour chapters are
deliberately excluded: their MP4 is published at full 1280 width.

One thing it cannot reach: the inline filter's input (`FilterBar QLineEdit`,
`styles.qss`) stays 9pt — that selector is not in `Theme._CSS_TO_QSS`, so no
user Theme.css can express it. Neither clip uses the inline filter.

### Clearing the desktop

The recording tool minimizes every visible top-level window before it starts
the launcher (`"minimize_all"` in its config, on by default). Two separate
things make a leftover window fatal to a take: the recorder grabs screen
*pixels* of fman's window rect, so anything drawn over it is burned into every
frame; and demo mode pins `DEMO_OPACITY` at 0.8, so whatever sits *behind* fman
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

Demo mode needs the app-side connector library. It is **not** in the normal
requirements — it lives in a dev-only file so it never enters a release build.
From the repo root:

    pip install -r requirements/windows-debug.txt

This installs [automated-screenshot-connector](https://github.com/BenjaminKobjolke/automated-application-screenshots-python-connector)
(expected as a sibling checkout: `../automated-application-screenshots-python-connector`).

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

**The interpreter matters.** fman's dependencies (PyQt5, fbs_runtime) are a
`pip --user` install, and the connector is an editable `.pth` install — both
live in that interpreter's user site-packages, so another `python` on `PATH`
(msys2's, a venv) will fail with `ModuleNotFoundError: fbs_runtime`. Point
`FMAN_PYTHON` at the right `python.exe` if plain `python` isn't it:

    set FMAN_PYTHON=C:\Program Files\Python314\python.exe

(The launcher already drops the tool's own `uv` virtualenv from `PATH`.)

## Recording checklist

1. **Close every always-on-top desktop widget** (clock/system-monitor gadgets,
   notification toasts, anything pinned above other windows). Ordinary windows
   are handled for you — the tool minimizes them before launching fman (see
   above) — but a window pinned above others survives that, and the capture is a
   screen region, so
   whatever is drawn over fman is burned into every frame and no setting in the
   tool can exclude it. The same goes for anything left *behind* fman: at
   `DEMO_OPACITY` 0.8 it shows through.
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
| the feature GIFs | `tools\demos_record.bat --demo 8`, then `--demo 9`, then `--compose features` (one demo per run — a second `--demo` overrides the first) |
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
- **3–7, the `tour-*` chapters** — the README's feature tour:

  | id | name | shows | measured |
  |----|------|-------|----------|
  | 3 | `tour-a-panes` | select, copy across panes, type-to-filter, sort | 302 frames, 30.2 s |
  | 4 | `tour-b-organize` | `F7` new folder, `F6` move, `Shift+F6` rename | 267 frames, 26.7 s |
  | 5 | `tour-c-viewers` | image viewer + zoom + next file, text viewer + edit/save | 328 frames, 32.8 s |
  | 6 | `tour-d-video` | video playing in the pane, and previewing into the other one | 276 frames, 27.6 s |
  | 7 | `tour-e-archives` | pack, browse inside the zip, copy out, fuzzy palette | 354 frames, 35.4 s |

- **8-9, the `feature-*` clips** - standalone, NOT part of the joined tour.
  They carry `"group": "feature"`, which the third `compose` step turns into the
  committed GIFs the README's feature index shows
  (`media/demos/features/goto.gif`, `tail.gif`):

  | id | name | shows | measured |
  |----|------|-------|----------|
  | 8 | `feature-goto` | `Ctrl+P` Go to: fuzzy jump, tab-complete, Enter | 101 frames, 20.2 s |
  | 9 | `feature-tail` | tail mode following a log while it grows | 105 frames, 21.0 s |

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
| frames held in RAM | ~3 MB each at 1280x800, and the MP4 export copies them all again as numpy arrays | ~30 MB per second at 10 fps — a single 2.5-minute take needs gigabytes |
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
| `"fps": 2` | `Recorder.request_still` saves the *next captured* frame, so at 2 fps a still lands within 0.5 s of the event — inside the 1.2 s the script keeps the palette closed afterwards |
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

For a tour chapter, pass its scratch folders instead (create them the way
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
| 8 `feature-goto` | the left pane ends on `projects\alpha` — and `Visited Paths.json` in the demo profile lists only `fman-demo-8-*` paths |
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
| `Screenshot(name)` | a `screenshot` event after 400 ms of settle | writes `media/demos/<demo>/<name>.png` |

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
5. For a `feature-*` or `plugin-*` clip, add its id to the `FONT_CSS` lines in
   `run_fman_demo.bat`, or it records at 9pt and the downscaled GIF is
   unreadable. Nothing else needs editing: the compose step picks up every demo
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
| the text in a `feature-*` or `plugin-*` GIF is too small to read | the demo-only `Theme.css` was not seeded - its id is missing from the `FONT_CSS` lines | add it in `run_fman_demo.bat` and re-record |
| a clock/monitor overlay is visible in every frame | an always-on-top desktop widget | close it and re-record; the capture is a screen region |
| file names or window contents show faintly *through* fman | a window was left behind fman, and `DEMO_OPACITY` is 0.8 | check the minimize count the tool logs — a zero on a bad take is the tell; a window pinned always-on-top survives the minimize and has to be closed by hand |
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
