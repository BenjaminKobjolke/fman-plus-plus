# Themes

How fman colors and styles its UI, how to switch themes, and how to write
your own.

## Switching theme

Open the [command palette](COMMAND_PALLETTE.md) (`Ctrl+Shift+P`) and run
**"Select theme"**. The list shows every installed theme, with the active one
preselected and marked `current`. Picking one applies it **immediately** — no
restart — and remembers it across restarts.

Bundled themes: **Monokai** (the default, fman's classic look), **Dark**,
**Light**, **Solarized Dark**, **Solarized Light**, **Nord**, **Dracula**,
**Gruvbox Dark**, **High Contrast**, **WezTerm**, **Matrix**,
**Windows 11 Light**, **Windows 11 Dark**. These imitate Windows 11 Explorer
and keep the System icons and default font on purpose (Segoe UI cannot be bundled).

What they look like, two seconds each (regenerate with
`tools\demos_record.bat --demo 2 --compose themes` — see [DEMOS.md](DEMOS.md)):

![themes](../media/demos/themes/themes.gif)

Two things do *not* recolor live:

- A **file viewer that is already open** (text, image or video). Those read
  their colors from the pane when they open, so close and reopen the file.
- **Context menus** on Windows and macOS. They deliberately imitate the
  native OS menu, and stay light under every theme — see
  [Not themed](#not-themed).

## Colors are data: one token map

Every color fman draws comes from one flat map of named **color tokens**
(`src/main/python/fman/impl/themes.py`, `DEFAULT_COLORS`). Those tokens feed
three consumers, which is why a theme cannot style one part of the UI and
leave another behind:

| Consumer | What it colors | How the tokens get there |
|----------|----------------|--------------------------|
| `src/main/resources/base/styles.qss` | File list, header, selection, inputs, status bar, overlays, quicksearch popup | `$token` placeholders, substituted by `Theme` (`impl/theme.py`) |
| `Plugins/Core/Theme.css` | Quicksearch **item** text: title, highlight, hint, description, item dividers, location-bar divider | same substitution — `Theme.load` substitutes every CSS file it loads |
| `QPalette` | Roles Qt draws itself: window chrome, tooltips, buttons, the pane focus rectangle, the "Loading…" text; also what the text viewer samples | `build_palette` & co. in `impl/themes.py` |

`ApplicationContext` reads the saved theme name before any plugin loads
(`%APPDATA%/fman/Local/Settings.json`, key `theme`) because the `QPalette`
has to exist when the `QApplication` is created.

## Writing a theme

A theme is **one JSON file** listing only the colors it changes (plus,
optionally, an [opacity](#opacity), [background images](#background-images),
an [icon set, an icon size and an icon color](#icons), and a
[font](#fonts)):

```json
{
	"colors": {
		"pane_bg": "#2e3440",
		"pane_fg": "#d8dee9",
		"pane_selected_fg": "#88c0d0"
	}
}
```

- **File name is the theme name.** `Nord.json` shows up as *Nord*.
- Put it in `%APPDATA%/fman/Themes/` (Windows; `~/Library/Application
  Support/fman/Themes` on macOS, `~/.config/fman/Themes` on Linux). A file
  there shadows a bundled theme of the same name.
- Bundled themes live in `src/main/resources/base/Themes/`.
- `Monokai.json` is `{}` — the defaults *are* Monokai, so there is no second
  copy of them to drift.
- Unknown token names and invalid color values are ignored, not fatal: a
  typo costs you that one color, it never stops fman from starting.
- Values are any color Qt understands (`#rgb`, `#rrggbb`, `white`). A value
  containing `;`, `{` or `}` is rejected — it would break out of the
  stylesheet rule it lands in.

### You only need the 16 core tokens

Tokens that are not listed **inherit from a parent token** before falling
back to the default. So setting `pane_bg` alone also moves `base_bg` (what
the text viewer paints on), and setting `border` alone moves every separator
and bevel in the quicksearch popup.

**Core tokens** — no parent, set these:

| Token | What it colors |
|-------|----------------|
| `pane_bg` | File list / dialog / overlay / filter-bar background |
| `pane_fg` | File rows |
| `pane_fg_dir` | Directory rows (defaults to `bright_fg`) |
| `pane_selected_fg` | Text of selected files |
| `pane_cursor_bg` | Cursor row, and the pane's focus rectangle |
| `header_bg` | Column-header gradient, input borders |
| `muted_fg` | Header text, labels, checkboxes, item descriptions |
| `bright_fg` | Input text, status-bar text, highlighted matches |
| `border` | Overlay / filter-bar border, status-bar top edge |
| `input_bg` | Text fields (rename editor, prompts) |
| `window_bg` | Window and dialog chrome |
| `statusbar_bg_top` | Status-bar gradient |
| `popup_bg` | Quicksearch / command-palette background |
| `popup_item_fg` | Command-palette entry titles |
| `popup_selected_bg` | Selected entry in the palette |
| `scrim_bg` | The dim over the main window while a dialog is open |

`scrim_bg` is the one token whose **alpha** matters, which is why it takes an
`#AARRGGBB` value: the alpha byte *is* how strong the dim is. `#80000000` (the
default) is 50% black, `#40000000` a quarter, and `#00000000` switches the
scrim off entirely — see [Dimming behind dialogs](#dimming-behind-dialogs).

Separators inherit `border`, never the surface they sit on: a divider that
defaults to `popup_bg` is invisible by construction, which is what made the
command palette read as one solid block in early versions of the light theme.

A theme that wants *no* separators at all sets `popup_divider_top` and
`popup_divider_bottom` to its own `popup_bg` explicitly — the inherited
fallback is never the surface, so this has to be said out loud. `Matrix.json`
does it; its rows are held apart by the green text alone.

**Derived tokens** — override only if the inherited value looks wrong:

| Token | Inherits from |
|-------|---------------|
| `base_bg` | `pane_bg` |
| `readonly_fg` | `muted_fg` |
| `input_border`, `locationbar_border`, `palette_midlight` | `header_bg` |
| `statusbar_bg_bottom` | `statusbar_bg_top` |
| `pane_statusbar_bg_top` | `statusbar_bg_top` |
| `pane_statusbar_bg_bottom` | `pane_statusbar_bg_top` |
| `pane_statusbar_fg` | `bright_fg` |
| `pane_statusbar_border` | `border` |
| `popup_query_border`, `popup_query_inner_border`, `popup_divider_top`, `popup_divider_bottom`, `popup_input_border` | `border` |
| `popup_input_bg` | `input_bg` |
| `popup_input_fg` | `bright_fg` |
| `popup_input_border_top` / `_left` / `_right` | `popup_input_border` |
| `main_window_bg`, `button_bg` | `window_bg` |
| `alt_row_bg` | `pane_cursor_bg` |
| `button_fg` | `muted_fg` |
| `palette_mid`, `palette_dark`, `palette_shadow` | `button_bg` |
| `pane_hidden_fg` | 60% of `pane_fg` unless set |
| `pane_hidden_fg_dir` | 60% of `pane_fg_dir` unless set |

Hidden file text uses `pane_hidden_fg`; hidden directory text uses
`pane_hidden_fg_dir`. For example, set either token under `colors` to choose
an explicit faded color: `"pane_hidden_fg": "#99aabbcc"`. Setting them to
`pane_fg` and `pane_fg_dir` keeps the text at its normal color while the
hidden-file icons remain gray.

### Dimming behind dialogs

While the command palette, pick lists or text prompts are open, fman draws them
inside the movable, resizable main window and lays a **scrim** over the file
list. Clicking the scrim closes them like Esc. Alerts and the progress dialog
remain separate windows; the progress dialog's palette stays modal. The scrim
is not a separate theme key — it is the `scrim_bg` color token, with its alpha
byte carrying the strength:

```json
{
	"colors": { "scrim_bg": "#40000000" }
}
```

- The scrim covers the **main window only**. Embedded palettes and prompts
  follow the window's opacity; separate alerts, file-open and progress dialogs
  stay opaque.
- It is drawn behind the command palette, pick lists and prompts. **Not** behind
  the progress dialog: a copy can run for minutes, and a window dimmed that
  long costs more than the contrast is worth.
- `#00000000` is a fully transparent scrim, i.e. the pre-scrim look. A theme
  that wants no dim at all says that.
- Unlike [opacity](#opacity) below, this is a plain color token, so it lives
  *in* `colors` and follows every rule the other tokens do.
- What the scrim is for, beside every other window-level function:
  [WINDOW_FUNCTIONS.md](WINDOW_FUNCTIONS.md#dimming-behind-dialogs).

### Opacity

A theme may also make fman's window see-through. This is one of six things
in a theme file that are *not* colors, so it sits beside `colors`, not in it:

```json
{
	"colors": { "pane_bg": "#000000" },
	"opacity": 0.92
}
```

- `1.0` is fully opaque, `0.3` the most transparent fman allows. A value
  outside that range, or one that is not a number, is ignored like any other
  typo — the theme just doesn't change the opacity.
- The whole window fades, text included. fman does not do background-only
  translucency. Embedded palettes and prompts follow that opacity; separate
  alerts and progress dialogs stay opaque.
- Leaving the key out means "don't touch it", which resolves to fully
  opaque — not "inherit from the previous theme". Switching themes therefore
  always sets the opacity, back to 1.0 included.
- The user's own setting wins over the theme's: see
  [Set window opacity](functions/window-opacity.md). Their choice survives a
  theme switch until they pick **Theme default** again.
- Bundled example: `Matrix.json`.

### Background images

A theme may also place **images** behind fman's UI — one behind the whole
window, or a different one per pane:

```json
{
	"colors": { "pane_bg": "#000000" },
	"backgrounds": [
		{ "image": "Matrix/wall.png", "target": "window" },
		{
			"image": "Matrix/corner.png",
			"target": "pane.1",
			"fit": "contain",
			"anchor": "bottom-right",
			"opacity": 0.6
		}
	]
}
```

`backgrounds` is a **list**, so a theme may place as many images as it
likes. Each entry takes:

| Key | Values | Default |
|---|---|---|
| `image` | Path to the file. Relative paths resolve against the theme's *own* `Themes` directory; absolute paths are allowed. **Required.** | — |
| `target` | Which surface it goes behind — see below | `window` |
| `fit` | `cover`, `contain`, `stretch`, `tile`, `none` | `cover` |
| `anchor` | `top-left`, `top`, `top-right`, `left`, `center`, `right`, `bottom-left`, `bottom`, `bottom-right` | `center` |
| `opacity` | `0.0`–`1.0`. Blended over the surface's own theme color, so `0.15` gives a watermark rather than a wallpaper. | `1.0` |

**Targets**

| `target` | Where the image is drawn |
|---|---|
| `window` | Behind everything: all panes, their column headers, and the status bar |
| `pane` | Behind every pane's file list |
| `pane.0`, `pane.1`, … | Behind one pane, counted from the left |
| `pane.active` | Behind whichever pane currently has focus |
| `pane.inactive` | Behind every pane that does not |

**Fit modes**

| `fit` | What it does |
|---|---|
| `cover` | Scaled up until it covers the surface, aspect ratio kept, overflow cropped. The usual wallpaper. |
| `contain` | Scaled until it fits entirely inside, aspect ratio kept, the rest left to the theme color |
| `stretch` | Scaled to the surface exactly, aspect ratio ignored |
| `tile` | Repeated across the surface at its own size. `anchor` does not apply. |
| `none` | Drawn at its own pixel size, not scaled at all. This is the one that docks artwork into a corner. |

There is no `fill`. **`cover`** is the crop-to-fill mode most people mean
by it; **`stretch`** is the one that ignores the aspect ratio.

`anchor` decides where the slack between image and surface goes. With
`none` and `contain` it positions the image; with `cover` it picks which
part survives the crop.

- **Where the files go.** Put them in a directory named after the theme,
  beside its JSON: `%APPDATA%/fman/Themes/MyTheme/wall.png`, written as
  `"image": "MyTheme/wall.png"`. That is what `Icons/<Name>/` already does
  for an icon set. Any format Qt can read works — PNG, JPEG, BMP, WEBP.
  Animated GIFs are not animated; only their first frame is drawn.
- **A pane image shows through the file names.** The pane stops painting
  its own `pane_bg`, so the image is visible behind the rows, not only in
  the empty space below them. The **cursor row** keeps its
  `pane_cursor_bg` fill so it stays readable over any artwork; selected
  rows give theirs up and are told apart by `pane_selected_fg` alone.
  Check the contrast — a busy image under `pane_fg` is the one way a
  theme can become genuinely hard to read.
- **A `window` image runs behind the chrome too.** The column headers,
  the location bars and the status bar go transparent for it, so one
  image spans the whole window uninterrupted. A *pane* image does not do
  this: it stays inside its pane, and the strips keep their theme colors.
- **A pane's own image wins.** Where both a `window` and a `pane` image
  apply, the pane paints its `pane_bg` and its own image over it — the
  window image does not show through that pane.
- **Order matters.** Entries are drawn in the order the file lists them,
  so a later one covers an earlier one on the same surface.
- **A bad entry costs the image, not fman.** A file that does not exist,
  a `fit` that is a typo, an `opacity` outside `0.0`–`1.0`: the entry is
  ignored, the rest of the theme applies, and fman starts normally — the
  same rule as every other value in a theme file. Unlike the other
  values, though, each rejection is **logged with the reason and the
  allowed values**, because an image that silently never appears gives
  you nothing to debug. Run fman from a terminal to see them.
- **This is not window transparency.** The images are drawn *inside*
  fman's window; nothing of the desktop behind it shows through. For
  that, see [opacity](#opacity) above.
- Bundled example: `Matrix.json`, whose artwork lives in `Themes/Matrix/`.

### Icons

A theme may also name an **icon set** for the file list, how big to draw it,
and what color to recolor it. All three sit beside `colors` — the first two
because they are not colors, and `icon_color` because it is a color that is
*not a token*: it is painted onto image files rather than substituted into a
stylesheet, so `resolve_colors` would have nothing to do with it.

```json
{
	"colors": { "pane_bg": "#2e3440" },
	"icons": "Material",
	"icon_size": 20,
	"icon_color": "#88c0d0"
}
```

- **`icons`** is `System` (the OS icons, the default) or the name of an
  installed set. `Material` ships with fman.
- **`icon_size`** is a whole number of pixels from 12 to 64. It applies to
  the `System` set too, and the rows grow with it. It also follows the
  [pane font size](functions/pane-font-size.md) zoom.
- **`icon_color`** is any color Qt understands. Each icon keeps its own
  shading and takes the color's hue. Only an icon set answers to it — the
  `System` icons are the shell's bitmaps and cannot be recolored, so a theme
  that wants colored icons has to name `icons` too.
- Leaving a key out means "don't touch it", so switching theme always sets
  all three — back to the defaults included. An unusable value is ignored
  like any other typo.
- The user's own choice wins over the theme's and survives a theme switch,
  until they pick **System** or **Theme default** again.
- Bundled example: `Matrix.json`, which asks for `Material` in its own green.

Icons are a topic of their own: what the sets are, which files keep their OS
icon, how to write your own, and how the bundled set is vendored — see
[**docs/ICONS.md**](ICONS.md) and
[Select icon set](functions/select-icon-set.md).

### Fonts

A theme may also name the **font family** the whole UI is drawn in. Like the
icon set, it sits beside `colors`:

```json
{
	"colors": { "pane_bg": "#000000" },
	"font": "Share Tech Mono"
}
```

- The value is a family **name**, not a file: any family Qt can see, which
  means the ones fman bundles *and* whatever is installed on the machine.
- A family this machine does not have is **not** an error — Qt falls back to
  its own font, so a typo costs you the typeface rather than the ability to
  start fman.
- Leaving the key out means "don't touch it", which resolves to fman's default
  for the platform (`Roboto` on Windows, `Open Sans` on Linux,
  `Helvetica Neue` on macOS) — so switching theme always sets the family,
  back to the default included.
- The user's own choice wins over the theme's and survives a theme switch,
  until they pick **Theme default** again.
- Only the *family* is a theme property. The **size** is not: that is
  [Theme.css](#themecss-fonts-padding-and-user-overrides) plus the user's
  [pane font size](functions/pane-font-size.md) zoom, and the two are
  independent.
- Bundled example: `Matrix.json`, which asks for Share Tech Mono beside its
  green Material icons.

Fonts are a topic of their own: which families ship, how to add one, how the
bundled ones are vendored, and why the directory name is read out of the font
file — see [**docs/FONTS.md**](FONTS.md) and
[Select font](functions/select-font.md).

### Not themed

- **`QMenu` in `os_styles.qss`** (Windows/macOS context menus) — these copy
  the native OS menu on purpose, which is why they are light while fman is
  dark. Theming them is a separate decision; the values stay literal.
- **`QPalette.Highlight`** — never set, so Qt's Fusion style supplies it.
  This is what the progress bar uses.
- **The icon *set*.** A theme picks which set is drawn, how big, and what
  color ([Icons](#icons)) — but the drawings are image files, so everything
  else about them is the set's, not the theme's. `icon_color` is a tint over
  the whole set, not a per-icon palette.
- **The `System` icons.** Those come from the Windows shell, GTK or the
  Finder, so `icon_color` does not reach them. A theme wanting colored icons
  names an `icons` set as well.
- **Font *size*, padding and every other metric.** A theme owns the font
  *family* ([Fonts](#fonts)) and `icon_size` — not how big the text is.
  For the rest, see `Theme.css` below and
  [Pane font size](functions/pane-font-size.md).

## Theme.css: fonts, padding, and user overrides

Separate from the color tokens, fman merges a small friendly stylesheet from
these files, each optional, in order:

- `Plugins/Core/Theme.css` — base rules (all platforms).
- `Plugins/Core/Theme (Windows|Mac|Linux).css` — platform-specific.
- `%APPDATA%/fman/Plugins/User/Settings/Theme.css` — **the user override
  file.** It loads last, so it wins over every theme. Edit this to change
  font sizes or padding, or to pin a color a theme keeps changing.

The base `Theme.css` takes the family from the active theme
(`* { font-family: $font_family; }`), so setting `font-family` in the
override file pins it against every theme the way pinning a color does.
[Select font](functions/select-font.md) is the supported way to do that,
though, and unlike an edit here it is undoable from the palette.

Put *only what you change* in that file. Copying the whole base `Theme.css`
into it copies its color literals too, and those then override every theme —
the classic symptom is a command palette that stays light-on-dark after
switching to a light theme.

Any plugin can ship a `Theme.css`; it is loaded per plugin at load time
(`impl/plugins/plugin.py`). `Theme` (`impl/theme.py`) understands only a
fixed set of selectors, mapped to real Qt ones (`_CSS_TO_QSS`):

| CSS selector | Real Qt selector |
|--------------|------------------|
| `*` | `*` (everything) |
| `th` | `QTableView QHeaderView::section` |
| `.statusbar` | `QStatusBar, QStatusBar QLabel, PaneStatusLine` |
| `.pane-statusbar` | `PaneStatusLine` |
| `.locationbar` | `LocationBar:read-only` |
| `.quicksearch-query` | `Quicksearch QLineEdit` |
| `.quicksearch-item` | `Quicksearch QListView::item` |

(`.quicksearch-item-title`, `-highlight`, `-hint` and `-description` are
parsed separately by a small CSS engine and read back by the popup's own
paint code via `Theme.get_quicksearch_item_css()`, rather than becoming QSS.)

Every font size in that group — the four above plus `.quicksearch-query` —
is multiplied by the [pane font zoom](functions/pane-font-size.md), which the
Core plugin pushes in through `Theme.set_font_scale()`. The four painted ones
are scaled in the dict; the query line gets a `Quicksearch QLineEdit`
font-size rule appended *after* everything else in the app stylesheet, which
is what makes the zoom beat your own `.quicksearch-query` rule. The sizes you
author stay the palette's 1.0 baseline.

Your `Theme.css` may contain `$` freely — substitution leaves unknown names
alone. To use a theme's color in it, write the token: `color: $pane_fg;`.

## The wildcard gotcha (why widgets sometimes look "stuck")

`* { font-size: 9pt; }` in the base `Theme.css` becomes a QSS `*` rule
applied to every widget. This has a side effect beyond font size: **once any
stylesheet touches a widget, Qt switches that widget from palette-based
rendering to the QSS style engine.** Two consequences seen in this codebase:

- A widget relying on `QPalette` colors alone may stop reflecting palette
  changes once the wildcard rule touches it, unless it also gets an explicit
  local QSS rule.
- QSS-rendered `QPlainTextEdit`/text widgets only draw the blinking caret if
  `color`/`background-color` are set **explicitly** in that widget's own
  stylesheet (hit by the text viewer, see
  [`docs/views/TEXT_VIEWER.md`](views/TEXT_VIEWER.md)).

**The fix pattern:** apply a narrow, widget-local QSS rule targeting only
that widget's type selector — a local rule always wins over the app-wide `*`
rule, and over the theme.

- [Pane font size](functions/pane-font-size.md) — sets
  `FileListView { font-size: Npt; }` locally, so it survives a theme switch.
- [Text viewer](views/TEXT_VIEWER.md) — sets `QPlainTextEdit { color: …;
  background-color: …; }` locally, with the colors read live from the pane's
  `QPalette` rather than hardcoded.

## Writing a new widget that should follow the theme

- **Colors:** read the inherited `QPalette` rather than hardcoding —
  `widget.palette().color(QPalette.Base)` for background,
  `QPalette.Text`/`QPalette.WindowText` for foreground, `QPalette.Highlight`
  for selection. In a delegate/paint routine use `option.palette`
  (`impl/view/__init__.py`). Never read `fman.impl.themes` directly from a
  plugin: the palette is the supported way to get theme colors.
- **Sizes/padding shared with the rest of the UI:** either add a selector to
  `_CSS_TO_QSS` (touches core, affects every theme file) or read the live
  effective value off an existing styled widget, the way pane-font-size reads
  `QFontInfo(view.font()).pointSize()`.
- **If you must set a local stylesheet:** keep it a narrow type-selector
  rule, not `*`, and source the colors from `QPalette`/a live widget so a
  theme switch still reaches it.

## Tests

`tools/run_theme_tests.bat` runs the engine's theme tests. (The icon set has
its own — see [ICONS.md](ICONS.md#tests).) The guards worth knowing about:

- Neither `styles.qss` nor `Theme.css` may contain a color literal, and
  every `$token` in them must exist — a mistyped placeholder would survive
  substitution and make the CSS parser reject the file, taking the whole
  Core plugin down.
- `build_palette(DEFAULT_COLORS)` is asserted against the exact `QPalette`
  fman used before themes existed, so the default look cannot drift.
- A bundled theme's optional `icons` must name an icon set fman actually
  ships, and its `icon_size` and `icon_color` must survive their loaders —
  an out-of-range size or an unparseable color would be silently ignored at
  runtime, which in a *bundled* theme is a typo nobody would notice. Its
  `font` clears the same bar, and must additionally be a family fman
  *bundles*: any installed family is legal in a theme you write, but a
  bundled theme naming one would look different on every machine.
- The bundled fonts have guards of their own — see
  [FONTS.md](FONTS.md#tests).
- Every bundled theme is checked for **legibility**, not just validity: text
  pairs (entry title, matched characters, shortcut hint, description, file
  and directory rows, column headers) must clear a 4.5:1 WCAG contrast
  ratio, separators must be visible against the popup, and the selected row
  must stand out from it. Monokai is exempt — it *is* the pre-themes look,
  pinned by the tests above, so it cannot be recolored to satisfy a ratio.
  Matrix is exempt from the *separator* check only: it drops the dividers on
  purpose (`_NO_DIVIDERS` in `test_themes.py`). The guard that a separator
  may never *inherit* its own surface still covers every theme.
  A bundled theme's optional `opacity` is validated the same way, and the
  count of bundled themes is asserted, so adding a file is a deliberate act.
  A new theme has to pass; add it to `src/main/resources/base/Themes/` and
  run the bat.
