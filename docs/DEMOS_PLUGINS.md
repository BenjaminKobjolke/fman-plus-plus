# Recording plugin demos

fman's demo machinery can film a **third-party plugin**, not just fman itself.
The result is one GIF published in two places: the plugin's row in the
[README's plugin list](../README.md#plugins), and the plugin's own README in
its own repository.

This page covers only what is specific to plugin clips. Everything shared — the
install, the step vocabulary, the recorder's RAM and timeout limits, the pane
sort order, the palette-query traps — is in [DEMOS.md](DEMOS.md), and you need
to have read that first.

One command records and builds everything on this page:

    tools\demos_record.bat --demo 10 --compose plugins

Rebuild the GIF from an existing take without re-recording:

    tools\demos_record.bat --compose plugins

## Why a category of its own

There are three demo prefixes and they are not interchangeable:

| group | name prefix | what it films | published as |
|-------|-------------|---------------|--------------|
| `tour` | `tour-*` | fman's own feature tour | `media/demos/tour/feature-tour.mp4` |
| `feature` | `feature-*` | one fman feature, standalone | `media/demos/features/*.gif` |
| `plugin` | `plugin-*` | a third-party plugin | `media/demos/plugins/*.gif` |

The **`group`** field in `fman.json` is what routes a demo — each compose step
picks up every demo in its group. The name prefix only shapes the output
filename: `{short}` in a step's `output` strips the group prefix, so
`plugin-matrix-rain` becomes `matrix-rain.gif`. Keep the two in agreement; a
clip put in the `tour` group is joined into the hero video no matter what it is
called.

What makes `plugin` a separate group rather than more `feature` clips is that
these film **software this repository does not ship**:

- They carry a prerequisite no other demo has — the plugin must be installed on
  the recording machine (see [The seeding contract](#the-seeding-contract)).
- They raise a question no other demo raises: *whose* copy of the plugin got
  recorded. The launcher copies your working checkout verbatim, uncommitted
  edits included.
- They are encoded differently, because plugin UI is often animated where fman's
  own is mostly static (see [Encoding](#encoding)).

## The seeding contract

`run_fman_demo.bat` wipes `%TEMP%\fman-demo-profile\Plugins` on **every** run,
before any per-id setup. That wipe is the whole reason recordings are
reproducible: a recordist's third-party plugins prepend their key bindings (so
they beat Core's) and add palette commands that change what a typed query
resolves to. Everything a demo needs is then written back into the fresh tree.

For id 10 that is:

| what | from | into |
|------|------|------|
| the plugin under test | `%APPDATA%\fman\Plugins\User\MatrixRain` | `Plugins\User\MatrixRain` |
| the demo font CSS | `tools/create_media/demo_Theme.css` | `Plugins\User\DemoFont\Theme.css` |
| right-pane fixtures | `examples/right_pane` | the run's scratch `RIGHT` folder |

**Seed the plugin under test and nothing else.** Copying all of
`%APPDATA%\fman\Plugins` would put your key bindings and palette commands back
into the take — exactly what the wipe exists to prevent — and the take would
look fine while quietly filming a different program than the one a viewer will
install. MatrixRain is safe to seed for the opposite reason: its
`Key Bindings.json` is `[]` by design, so it steals no chord from Core.

Plugin load order is shipped → `Third-party\` → `User\`, with `User\Settings`
forced last (`fman/impl/plugins/discover.py`). Seeding under `User\` therefore
reproduces what a user who copied the plugin in by hand would get.

**A missing plugin aborts the run.** This is deliberately *not* a warning like
the missing-libmpv one: an absent libmpv degrades a take you can still judge by
eye, whereas an absent plugin produces a perfectly clean recording of fman
*without* the plugin, in which every palette query matches nothing and the panes
simply never change. The launcher exits 1 with:

    ERROR: MatrixRain is not installed in %APPDATA%\fman\Plugins\User - cannot record demo 10.

## The MatrixRain clip

`plugin-matrix-rain` (id 10) shows the rain in **one pane**, then in **both**.

| step | what is on screen |
|------|-------------------|
| palette → `matrix rain in other pane` | the right pane rains; the left is still a file list |
| palette → `matrix rain transparency` → `70` | the right pane's rain goes translucent, its file list showing through |
| palette → `matrix rain` | the left pane rains too — both panes, both translucent |
| `Escape`, `Tab`, `Escape` | back to two file lists |

Two things about that order are not stylistic.

**The other-pane command comes first on purpose.** MatrixRain has no "both
panes" command — only *Matrix rain* (this pane, takes focus) and *Matrix rain in
other pane* (the other pane, focus stays put). Running the other-pane one first
is what produces one-pane-then-both at all. It also keeps the keyboard in the
left **file list** for every palette step: `MatrixRainView.keyPressEvent`
swallows Escape/Return/Backspace/Tab and only forwards the rest, so whether
`Ctrl+Shift+P` reaches Core's palette from inside a mounted rain widget is
untested. This ordering never has to find out.

**Every query is an exact alias.** `match_titles_or_keywords`
(`core/quicksearch_matchers.py`) returns bucket 0 for a query that *equals* a
lowercased alias, ahead of every fuzzy tier — so `matrix rain`,
`matrix rain in other pane` and `matrix rain transparency` each resolve to
exactly one command, with no shortest-title tie-break involved. That is a
stronger guarantee than the `view file` / `comp dir` queries in
[DEMOS.md](DEMOS.md) get, and it is worth preserving here specifically: a
plugin's command titles are outside this repository's control, so a query that
relies on ranking can be broken by an edit in someone else's repo.

The clip is **34.1 s scripted**, about 35.6 s of wall clock once the player's
500 ms start delay and 1 s end hold are counted. That is inside `DEMO_CAP_S`
(300 s) and under `EVENT_TIMEOUT_S` (60 s) on `demo_started` alone, so it needs
no `Screenshot` heartbeats.

Its settings are deterministic without any seeding: the plugin persists through
Core into `Plugins\User\Settings\Matrix Rain (Windows).json`, which is inside
the wiped tree, so every run starts at the plugin's own defaults
(`transparency: 0`, `fps: 20`, `columns: 0`) and the transparency prompt always
opens on the same value.

## Encoding

The plugin GIFs use the same `mp4_gif` compose step as the feature GIFs — the
same two-pass `palettegen`/`paletteuse`, plus a `gifsicle` pass when `lossy` is
set. What differs is every number, and each one was measured on the MatrixRain
clip rather than guessed:

```json
{"type": "mp4_gif", "group": "plugin", "output": "demos/plugins/{short}.gif",
 "fps": 4, "width": 360, "colors": 32, "lossy": 60}
```

| knob | feature GIFs | plugin GIFs |
|------|--------------|-------------|
| `width` | 800 | **360** |
| `fps` | 5 | **4** |
| `colors` | 64 | **32** |
| `lossy` | — (absent) | **60** (`gifsicle -O3 --lossy=60`) |

Matrix rain is close to the worst case for GIF: every pixel changes every frame,
so inter-frame delta compression buys nothing and each frame is stored whole. At
the feature clips' settings the same 34 s take came out at **7.1 MB**.

**What did not help**, all measured on that take:

| change | result |
|--------|--------|
| 64 → 24 colours | 7.1 → 6.6 MB |
| dithering off | no change |
| `paletteuse=diff_mode=rectangle` | no change |
| `palettegen=stats_mode=diff` | no change |

The last two are the ones worth knowing about, because they *sound* like the
right tool: both exploit regions that stay still between frames, and this clip
has none. Only two levers move the number at all.

**Pixel count.** The dominant term. It is also where the original 640 px was
simply wasteful: the README renders this GIF at 360, so encoding at 640 paid
four times the pixels to throw them away.

Whether you can afford a small width depends on what the clip demonstrates.
The `feature-*` clips show *reading and typing* — a fuzzy query being matched, a
log being followed — so their text has to stay legible, which is what the 800 px
and the [demo font CSS](DEMOS.md) are for. This one demonstrates an **effect**;
nobody needs to read the file names to see rain fill one pane and then both. A
plugin clip that does hinge on text needs a wider setting and a bigger budget.

**`lossy`.** Worth about 40%. It lets nearly-identical pixels share a palette
entry — exactly the redundancy a rain of glyphs has, and exactly what ffmpeg's
palette stage cannot exploit. It is the one lever ffmpeg does not have, which is
why the compose step shells out to `gifsicle` for it. Optional: without gifsicle
on `PATH` the step warns and ships the larger file.

Together those two put the shipped GIF at **1.4 MB** for the full 34 s clip.

Budget: **~1.5 MB**. If a clip overshoots, in order:

1. lower `width` — by far the biggest lever
2. raise `lossy` (100 is the practical ceiling before banding shows)
3. lower `fps`, accepting that the motion gets choppier
4. shorten the holds in the script and re-record

The first three are keys on the compose step in `fman.json`.

Or hand the whole ladder to the tool, which is what the budget mechanism is for:

```json
{"type": "mp4_gif", "group": "plugin", "output": "demos/plugins/{short}.gif",
 "fps": 4, "width": 360, "colors": 32, "lossy": 60,
 "max_size": "1.5MB", "fit": ["lossy", "colors", "width"]}
```

It encodes with exactly those settings first, and only if that overshoots does
it start spending the knobs in `fit` — `lossy` before `colors` before `width`,
because that order costs the least first. `fps` is deliberately left out, so it
is never traded: a plugin clip that drops frames misrepresents how the plugin
runs (see [Calibrate the capture fps](#calibrate-the-capture-fps)). At most
three encodes run, and the largest attempt that fits is the one kept.

## Calibrate the capture fps

The likeliest way a plugin clip ships wrong. The recorder writes the frames it
actually captured at whatever fps the config names, so a config fps *above* the
real capture rate makes the clip play fast and misrepresent how fast the
software is. [DEMOS.md](DEMOS.md) already records this happening at ~4.8 fps
with an animated theme merely sitting *behind* the window.

A plugin that animates two whole panes is heavier than anything else recorded
here, so treat this as a required step, not a check:

1. Record once at the configured `fps` (5 for id 10).
2. Divide the frame count the tool prints by the clip's wall-clock seconds
   (35.6 for id 10).
3. If the result is meaningfully lower, put that value in the **demo's** `fps`
   in `fman.json`, then re-record. The GIF's own `fps` is a separate key on the
   compose step: it may be lower than the capture rate (4 vs 5 here, to save
   bytes) but never higher, or the GIF invents frames the take never had.

## Publishing

The same GIF goes to two repositories:

- **fman** — `media/demos/plugins/<name>.gif` is committed; the recorded
  `media/demos/plugin-*/demo.mp4` is a gitignored intermediate. The README's
  plugin table shows it with inline HTML (`<img width="360">`, its native size),
  because Markdown
  image syntax cannot constrain width inside a table cell.
- **The plugin's own repo** — the installed checkout under `%APPDATA%` *is* the
  plugin's repository, so the finished GIF belongs there too. Copy it across
  yourself after composing:

      copy /y media\demos\plugins\matrix-rain.gif "%APPDATA%\fman\Plugins\User\MatrixRain\media\"

  **Committing and pushing it there is yours to do** — this repo has no business
  writing history in another one, which is also why the copy stayed a manual
  step rather than becoming a feature of the recording tool.

## Add another plugin demo

1. Install the plugin under `%APPDATA%\fman\Plugins\User\`, and commit whatever
   you want filmed — the launcher copies your working tree verbatim.
2. Add a `DemoScript` to `PLUGIN_CLIPS` in
   `src/main/python/fman/impl/demo_scripts.py` with a new id and a `plugin-*`
   name. Prefer palette queries that **equal** an alias exactly, and verify
   chords against the plugin's `Key Bindings.json` as well as Core's.
3. Add the matching entry to `demos` in `tools/create_media/fman.json`
   (`fps: 5` to start, `formats: ["mp4"]`, 1920x1080) with
   **`"group": "plugin"`** — that alone is what routes it into the plugin GIF
   step, and `{short}` names the output after the part following `plugin-`.
4. In `tools/create_media/run_fman_demo.bat`, choose the font file for the new
   demo: use `demo_Theme_default.css` for the tour-style Core sizes, or add its
   id to the `demo_Theme.css` override lines for a standalone clip that needs
   the larger font. Add a seeding block that copies **only that plugin** and
   exits 1 if it is absent.
5. Nothing to add to any build script: the existing compose step already picks
   up every demo in the group. If the new clip needs different encoder settings
   than MatrixRain's (a clip whose text has to stay legible wants a wider
   `width`), give it its own `mp4_gif` step with `"demo": "<name>"` instead of
   `"group": "plugin"`.
6. Record and build with `tools\demos_record.bat --demo <id> --compose plugins`,
   calibrate the fps, check the GIF size.
7. Publish both copies: the right-hand cell of that plugin's block in this
   repo's README (each plugin is a `###` heading over a two-column
   description/demo table), and the plugin's own README.

If `demo_scripts.py` passes 300 lines, split `PLUGIN_CLIPS` into
`demo_scripts_plugins.py` and `DEMOS.update()` it in — the same move
`demo_scripts_tour.py` already makes for the tour chapters.

## Troubleshooting

Start with [DEMOS.md](DEMOS.md); these rows are specific to plugin clips.

| symptom | cause | fix |
|---------|-------|-----|
| `ERROR: MatrixRain is not installed...` and no recording | the plugin is not in `%APPDATA%\fman\Plugins\User` | install it there; this is a hard stop by design |
| the take is clean but nothing ever happens on screen | the plugin was not loaded, so every palette query matched nothing | check `%TEMP%\fman-demo-profile\Plugins\User\<Plugin>\` exists after the run |
| a palette query opens the wrong thing | the plugin renamed a command, or a Core command title now matches better | re-check the alias; prefer a query that equals an alias exactly |
| the GIF is several megabytes | full-frame animation defeats GIF delta compression | walk the ladder under [Encoding](#encoding), or give the step a `max_size` and let it walk the ladder for you |
| the build warns that gifsicle is not on `PATH` | `lossy` is set but gifsicle is not installed | install it, or drop `lossy` and accept roughly double the size |
| the compose step builds nothing | the demo has no `"group": "plugin"` | add it; `tools\demos_record.bat --list` shows every demo's group |
| the clip plays faster than the software runs | capture could not hit the configured fps | recalibrate; see [Calibrate the capture fps](#calibrate-the-capture-fps) |
| the plugin's README shows an old clip | the copy step only runs when the checkout exists, and never commits | re-run the build, then commit in the plugin's repo |
