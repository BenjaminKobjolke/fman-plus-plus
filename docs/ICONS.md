# Icons

Which pictures the file list draws next to each file and folder, how big,
and how to ship your own set.

## Icon sets

By default fman shows the icons your operating system supplies — the Windows
shell, GTK on Linux, the Finder's on macOS. That is the **`System`** set, and
it is what fman has always done: one grey page for every text-ish file, one
folder for every folder.

On Windows, OS icons are fetched in the background as files load, so a slow
shell lookup does not stall drawing or scrolling. See
[Shell icons are fetched by the worker](LARGE_DIRECTORIES.md#shell-icons-are-fetched-by-the-worker).

An **icon set** replaces them with a picture per file type. One ships with
fman:

- **`System`** — the default. The OS icons.
- **`Material`** — the [Material Icon
  Theme](https://github.com/material-extensions/vscode-material-icon-theme)
  (MIT), the set VS Code users know: a distinct icon per language, per
  well-known config file and per well-known folder name. 829 icons in
  `src/main/resources/base/Icons/Material/`.

## Switching

Open the [command palette](COMMAND_PALLETTE.md) (`Ctrl+Shift+P`) and run:

| Command | What it does |
|---------|--------------|
| **Select icon set** | Pick a set. Both panes redraw immediately, no restart. |
| **Set icon size** | 16, 20, 24, 32 or 48 pixels, or **Theme default**. |
| **Set icon color** | Recolor the set — Green, Cyan, Blue, Amber, Red, Magenta, White, Grey — or **Theme default**. |
| **Toggle real icons for programs and shortcuts** | Opt `.exe` and `.lnk` back out of the set. |

None of them needs a restart, and all of them are remembered. Full usage,
hidden search keywords and how to bind them to a key:
[Select icon set](functions/select-icon-set.md).

The rest of fman's appearance is reachable the same way, and each is
remembered the same way: [Select theme](functions/select-theme.md) for the
colors, [Set window opacity](functions/window-opacity.md) for
see-through-ness, [Toggle title bar / Toggle menu
bar](functions/window-bars.md) for the window chrome above the panes, and
[Pane font size](functions/pane-font-size.md) — which, along with the icon
size, decides how tall a row is.

## Icon size

A whole number of pixels from **12 to 64**. It applies to the `System` set
too, so it is worth setting even if you keep the OS icons.

**The rows grow with it.** Row height is derived from the icon size and the
[pane font size](functions/pane-font-size.md) together, so a file list at
`48` is a very different thing to look at than one at `16`. If the rows are
taller than the font explains, this is why.

Leaving it unset means "don't touch it" — Qt draws at its own default, 16px.

### It follows the font zoom

**`Alt+Up` and `Alt+Down` move the icons too.** The
[pane font size](functions/pane-font-size.md) zoom scales the icons by the
same proportion it scales the text, so one pair of keys zooms the whole file
list rather than leaving 16px icons beside 20pt text.

It scales from *your* size, not from 16: at **Set icon size** `48`, zooming
in grows the icons from 48. The 12–64 range still caps it, so a long zoom
stops the icons before it stops the text. **Reset font size** puts both back.

The zoom is not stored separately — it is derived from the saved
`pane_font_size`, so *Set icon size* keeps showing the size you picked
rather than whatever the current zoom happens to draw.

## Icon color

An icon set can be **recolored**. Each icon keeps its own light and dark
areas and takes the color's hue, so a Material icon still reads as itself
rather than flattening into a silhouette — which is what makes a per-file-type
set worth recoloring at all.

Only an icon set answers to this. The **`System`** icons are the shell's own
bitmaps, so a color has no effect until you pick a set.

### What a tint costs

An untinted SVG stays a *drawing*: Qt's SVG engine redraws it crisply at
whatever size the view asks for. Recoloring has to happen on pixels, so a
tinted icon is rasterized **once at 128px** and scaled from there.

Two consequences, neither of which you are likely to notice, but both real:

- **Edges resample slightly differently.** A tinted icon at 24px is a
  128→24 downscale; the same icon untinted is drawn at 24px directly. The
  shapes match, but antialiased edge pixels differ a little. Measured on the
  bundled set at 48px: around 150 edge pixels differing by at most 42/255 in
  alpha, and no color shift at all.
- **128px is the ceiling, and `icon_size` 64 sits right at it.** At the
  maximum size on a HiDPI screen Qt asks for 64 × 2 = 128 real pixels, which
  is exactly what the tint rendered. Nothing softens today; there is simply
  no headroom left above it, so raising `MAX_ICON_SIZE` would mean raising
  `TINT_RENDER_SIZE` (`icon_tint.py`) with it.

Untinted icons have neither limit — leaving *Set icon color* on **Theme
default** keeps the pure-SVG path.

## A theme can carry all three

Icons are a [theme](THEMES.md) property. Beside `colors`, a theme file may
name an icon set, a size and a color, exactly the way it may carry an
[opacity](THEMES.md#opacity):

```json
{
	"colors": { "pane_bg": "#2e3440" },
	"icons": "Material",
	"icon_size": 20,
	"icon_color": "#88c0d0"
}
```

`Matrix.json` is the bundled example: it asks for `Material` in green, which
is why it is the one theme whose icons match the rest of it.

**Your own choice wins over the theme's**, and survives a theme switch — the
same precedence opacity uses:

| | |
|---|---|
| 1. | Your setting, if you have one (`Settings.json`: `icon_set`, `icon_size`, `icon_color`) |
| 2. | What the active theme asks for |
| 3. | `System`, Qt's own 16px, and the icons' own colors |

Picking **System** in *Select icon set*, or **Theme default** in *Set icon
size* or *Set icon color*, drops your override so the theme decides again.
Leaving a key out of a theme means "don't touch it", so switching theme
always sets all three — back to the defaults included.

An unusable value is ignored like any other typo, and costs you only that
one thing: a size that is not a whole number or is outside 12–64, an `icons`
value naming a set that isn't installed, or an `icon_color` that is not a
color Qt understands.

## Files that keep their OS icon

- **`.ico` files** always show themselves. An icon file *is* a picture of
  itself, and no set can say more about it than that.
- **Programs and shortcuts** (`.exe`, `.lnk`) use the icon set by default.
  A set draws every program alike, while the OS icon says *which* program it
  is — worth more in a folder full of them. **"Toggle real icons for programs
  and shortcuts"** opts those two extensions back out.
- **Files on network drives** already avoid the OS icon for an unrelated
  reason: asking the shell for a `.exe`'s icon on a share reads that file
  over the wire. See [Getting real icons back on network
  drives](WINDOWS_NETWORK_SUPPORT.md#getting-real-icons-back-on-network-drives).
  An icon set answers there without touching the wire, so it is the cheaper
  option, not a slower one.

## Overlay icons

Windows shell overlays show per-file status marks such as TortoiseSVN's
modified indicator. They are **off by default** because Windows must look up
each file's icon separately, which can slow very large folders. Use
**Toggle overlay icons** in the command palette to turn them on; the setting
is `shell_overlay_icons` in `Core Settings.json`.

When enabled, the System set uses the file's own Windows icon. Other icon sets
keep their chosen file-type icons and draw the Windows overlay over them. The
overlay is composed at the icon's size and cached by icon and overlay type.
Windows network paths stay excluded unless `network_file_icons` is also enabled,
because shell lookups can read files over the network.

fman listens for Windows shell change notices and batches them for 300 ms.
After a commit or revert, it invalidates and reloads only panes showing an
affected folder, without requiring Refresh. Turning overlays off suppresses
these refreshes too.

The implementation lives in:

- `src/main/python/fman/impl/model/shell_icons.py` — per-file Windows icons
- `src/main/python/fman/impl/model/shell_overlays.py` and
  `overlay_compose.py` — overlay lookup and drawing for icon sets
- `src/main/python/fman/impl/shell_change_notices.py` — Windows notices and
  debounced pane refresh
- `src/main/python/fman/impl/application_context.py` — Windows lifecycle wiring
- `src/main/resources/base/Plugins/Core/core/commands/window.py` — setting
  toggle command
- `src/unittest/python/fman_unittest/impl/test_shell_change_notices.py`,
  `impl/model/test_shell_overlays.py`, `test_overlay_compose.py`, and
  `test_icon_provider.py` — focused coverage, run with
  `tools\run_icon_tests.bat`

## Writing your own icon set

An icon set is a **directory**, not a file. Put it in
`%APPDATA%/fman/Icons/<Name>/` (`~/Library/Application Support/fman/Icons`
on macOS, `~/.config/fman/Icons` on Linux). The directory name is the set
name, and it shadows a bundled set of the same name — the same rule
[themes](THEMES.md#writing-a-theme) follow.

```
My Icons/
	manifest.json
	svg/
		file.svg
		folder.svg
		python.svg
		...
```

`manifest.json` is the [VS Code file icon
theme](https://code.visualstudio.com/api/extension-guides/file-icon-theme)
shape, reduced to the five keys fman reads. Every one is optional:

| Key | What it does |
|-----|--------------|
| `fileNames` | Whole file name → icon name (`"dockerfile": "docker"`) |
| `fileExtensions` | Extension → icon name (`"ts": "typescript"`) |
| `folderNames` | Folder name → icon name (`"src": "folder-src"`) |
| `file` | The icon for a file nothing else matched |
| `folder` | The icon for a folder nothing else matched |

Matching order for a file is `fileNames`, then `fileExtensions`, then
`file`. A folder only ever consults `folderNames` and `folder` — a directory
called `foo.ts` is still a directory.

**The longest extension wins.** `fileExtensions` is matched against every
dotted suffix, longest first, so `foo.d.ts` takes the `d.ts` icon rather
than the `ts` one. The bundled manifest has over 200 multi-dot keys, so
getting this backwards would give every TypeScript declaration file the
plain TypeScript icon.

Lookups are case-insensitive and **every manifest key must be lower-case** —
fman lower-cases the file name, not your keys.

An icon name resolves to `svg/<name>.svg`. Naming an icon the set doesn't
ship is not an error: that file just falls back to the OS icon, the same as
a name the manifest never mentions. Names may only contain letters, digits,
`.`, `_` and `-`, so a manifest cannot reach outside its own `svg/`.

Any format Qt can read works, but the file must be named `.svg`. SVG is what
the bundled set uses, and it is the only thing that stays sharp at
`icon_size` `48`.

You do not have to author a second set in another color: a theme's
[`icon_color`](#icon-color) recolors whatever set is active, and it works on
a hand-written set exactly as it does on Material. Author your set in its own
colors and let the theme tint it.

Color is the only thing a theme changes *inside* an icon. Everything else
about the drawing is the file — a set is a folder of images, not color
tokens. See [Not themed](THEMES.md#not-themed).

## Updating the bundled Material set

```bash
tools\fetch_material_icons.bat
```

It pulls the npm package, keeps only the mappings fman reads
(`fileExtensions`, `fileNames`, `folderNames` and the two fallbacks) and
copies only the icons those mappings name — 829 of upstream's 1251. Upstream
also maps a couple of dozen names it ships no file for; those mappings are
dropped and reported, so the manifest never promises a file that isn't
there.

Its output is committed on purpose: fman must never need the network to draw
an icon. Pass `--version 5.38.1` to pin a release instead of taking the
latest.

The vendored SVGs and manifest are excluded from the knowledge graph via
`.graphifyignore` — 8000 extension keys read as symbols would otherwise be
the single largest community in the repo.

## Tests

```bash
tools\run_icon_tests.bat
```

Three guards worth knowing about:

- **Every icon the bundled manifest can name has a file.**
  `fetch_material_icons` writes both the manifest and the SVGs; if it
  half-ran, the manifest would promise icons that aren't there and every one
  of those files would silently fall back to the OS icon — a failure that
  looks like nothing at all.
- An icon name is refused unless it is letters, digits, `.`, `_` and `-`,
  and a set name unless it is free of path separators. A hand-written
  manifest must not be able to read outside its own directory.
- **A transparent pixel stays transparent under a tint.** Icons are mostly
  transparent, so a recolor that got this wrong would draw a solid colored
  block per file — and a recolor that skipped its desaturating pass would
  turn a blue icon near-black under a green theme rather than green. Both
  are pinned in `test_icon_tint.py`.

## Where it lives

- `src/main/python/fman/impl/model/icon_set.py` — the manifest and its
  lookup rules
- `src/main/python/fman/impl/model/icon_provider.py` — the single choke
  point every icon fman draws goes through
- `src/main/python/fman/impl/model/table.py` — the other half of "redraws
  immediately": `Row.__eq__` ignores the icon by value, so dropping the caches
  is not enough. `invalidate_icons()`, which the provider calls when the set
  or color changes, is what makes the reload's diff actually replace the rows
- `src/main/python/fman/impl/model/icon_tint.py` — the recolor itself. Split
  out because it is pure `QImage`, which works without a `QApplication` and
  so can be tested; the `QPixmap` and `QIcon` around it cannot
- `src/main/python/fman/impl/themes.py` — the `icons` / `icon_size` /
  `icon_color` theme keys and their validators, plus `scale_icon_size`
- `src/main/python/fman/impl/theme_controller.py` — resolving your choice
  against the theme's, and pushing the result out. `set_icon_scale` is the
  font zoom's way in, and is deliberately the one appearance value that is
  not saved here
- `src/main/python/fman/impl/widgets.py` — `set_file_list_icon_size`, and
  `src/main/python/fman/impl/view/uniform_row_heights.py`, which recomputes
  the row height when the icon size changes
- `src/main/resources/base/Plugins/Core/core/commands/theme.py` —
  `SelectIconSet`, `SetIconSize`, `SetIconColor`
- `src/main/resources/base/Plugins/Core/core/commands/pane_view.py` — the
  pane font size commands, which is where the icon zoom factor comes from
- `src/main/resources/base/Icons/Material/` — the bundled set
