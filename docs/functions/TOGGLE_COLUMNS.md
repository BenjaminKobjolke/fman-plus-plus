# Toggle columns

Command palette entries and the file-list header menu let you hide or show
columns in the file panes, for people who mostly care about file names.

## Usage

1. Open the command palette and search "column".
2. Run **"Toggle size column"** to hide the Size column; run it again to show
   it. Same for **"Toggle modified column"** and the Modified column.
3. Right-click a column header to toggle any available column, including
   columns supplied by plugins. Both panes change together, and the choice
   survives restarting fman. The first column (normally Name) is always shown.

## Commands

| Command name              | Palette label          | Keywords                          | Default key binding |
|----------------------------|-------------------------|------------------------------------|----------------------|
| `toggle_size_column`       | Toggle size column      | show / hide size column            | none (palette only)  |
| `toggle_modified_column`   | Toggle modified column  | show / hide modified column, date  | none (palette only)  |
| `toggle_extension_column`  | Toggle extension column | show / hide extension               | none (palette only)  |
| `toggle_version_column`    | Toggle version column   | show / hide version                 | none (palette only)  |
| `toggle_attributes_column` | Toggle attributes column| show / hide attributes, permissions | none (palette only)  |
| `toggle_fixed_column_widths` | Toggle fixed column widths | fixed / auto-fit column widths | none (palette only) |
| `toggle_name_without_extension` | Toggle name without extension | hide extension in name | none (palette only) |

The other words listed under *Keywords* are hidden search terms: they find
the command in the palette without ever being shown. See
[the command palette](../COMMAND_PALLETTE.md#hidden-search-keywords).

These can be bound to a key in `Key Bindings.json` like any other command,
e.g.:

```json
{ "keys": ["Ctrl+Alt+S"], "command": "toggle_size_column" }
```

## Notes

- The hidden state for Size, Modified, Extension, Version, and Attributes
  remains in their existing `hide_size_column`, `hide_modified_column`,
  `hide_extension_column`, `hide_version_column`, and
  `hide_attributes_column` keys in `Core Settings.json`. Hidden plugin columns
  are stored by qualified name in its `hidden_columns` list and stay hidden
  when a plugin includes them in a column set. Extension, Version, and
  Attributes start hidden by default.
- Extension shows the last suffix (`archive.tar.gz` → `gz`); dotfiles and
  extensionless files have an empty value. Version shows Windows executable
  and library versions. Attributes shows `rhsa` flags on Windows and
  `rwxr-xr-x` permissions on macOS/Linux.
- `name_without_extension` defaults to `false`. When enabled with Extension
  visible, Name shows only the stem; in-place rename still preserves the
  hidden extension.
- `fit_name_column` in `Core Settings.json` defaults to `true` (auto-fit): Size
  and Modified use widths that fit representative values, and Name takes the
  remaining pane width. The Size sample covers a large file, and the Modified
  sample covers a long formatted date. Run **"Toggle fixed column widths"** to
  set it to `false`: Size and Modified keep their representative-value widths,
  while Name takes the remaining width. Other visible columns continue to fit
  their contents. Dragged column widths are remembered per pane across
  navigation and restarts. The palette toggle applies immediately to both
  panes.
- The vertical scrollbar starts below the column header. Its width is reserved
  during column sizing, including before Qt reports the scrollbar as visible.
- Hidden columns no longer reserve width in the file list.
- Every column after the first can be toggled this way — the first column is
  always shown.
- Column visibility is reapplied when navigating and when a plugin changes the
  column set, as well as on startup.
- On locations that don't have a Size or Modified column at all (e.g. the
  Windows drives list, `This PC`), toggling elsewhere has no effect there —
  there's nothing to hide.
- Toggling takes effect on both panes immediately, without needing to
  navigate or resize the window. The remaining visible columns' widths are
  recalculated to fill the pane right away, the same auto-fit that normally
  runs after loading a folder.

## Implementation

Core applies saved visibility to each live file view and reapplies it when the
column set changes or a pane navigates. The five built-in settings keys remain
unchanged; other columns use qualified names in `hidden_columns`. The
column-header menu is built from the current pane's columns and omits the first
column, which cannot be hidden.

Plugins choose the columns themselves through `fman.fs.set_default_columns()`
and `fman.fs.set_columns()`. Folder choices persist in `Column Settings.json`;
visibility choices persist separately in `Core Settings.json`. See
[`PLUGINS_API.md`](../PLUGINS_API.md#choosing-columns) for the API and lookup
order.

Column visibility is applied to the live Qt view. Core temporarily suppresses
its resize handler while hiding or showing a section, then recalculates the
remaining visible column widths so the change takes effect immediately.
