# Toggle columns

Command palette entries and the file-list header menu let you hide or show
columns in the file panes, for people who mostly care about file names.

## Usage

1. Open the command palette and search "column".
2. Run **"Toggle size column"** to hide the Size column; run it again to show
   it. Same for **"Toggle modified column"** and the Modified column.
3. Right-click a column header to toggle any available column. Both panes
   change together, and the choice survives restarting fman.

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

- The hidden state is stored in `Core Settings.json` under the
  `hide_size_column` / `hide_modified_column` keys. The Extension, Version,
  and Attributes columns start hidden, using `hide_extension_column`,
  `hide_version_column`, and `hide_attributes_column` (default `true`).
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
- Only the Size and Modified columns can be toggled this way — the Name
  column is always shown.
- Because the column set is owned by the current file system and rebuilt on
  every navigation, the hidden state is re-applied each time you move to a
  new folder, and again on startup.
- On locations that don't have a Size or Modified column at all (e.g. the
  Windows drives list, `This PC`), toggling elsewhere has no effect there —
  there's nothing to hide.
- Toggling takes effect on both panes immediately, without needing to
  navigate or resize the window. The remaining visible columns' widths are
  recalculated to fill the pane right away, the same auto-fit that normally
  runs after loading a folder.

## Implementation

- `src/main/resources/base/Plugins/Core/core/commands/columns.py` —
  `ToggleSizeColumn`, `ToggleModifiedColumn`, `ToggleFixedColumnWidths`
  (`DirectoryPaneCommand` subclasses), plus `InitColumnVisibility`
  (`DirectoryPaneListener`) which
  re-applies the saved visibility on startup and after every navigation
  (`on_path_changed`) — mirrors the existing `InitPaneFontSize` pattern.
- `src/main/python/fman/fs.py` defines the default `Column.get_widest_str()`
  hook; Core's `Size` and `Modified` columns provide representative values in
  `src/main/resources/base/Plugins/Core/core/__init__.py`.
- Column visibility is set directly on the Qt view:
  `pane._widget._file_view.setColumnHidden(index, hidden)`. There is no
  `pane.set_columns(...)` in the fman API — the file system owns the column
  set (`get_default_columns`) and the model is rebuilt on every navigation,
  so hiding/showing happens on the live widget instead, the same way the
  pane-font-size feature sets a stylesheet directly on
  `pane._widget._file_view`.
- Column identity is resolved by qualified name (`core.Size`, `core.Modified`)
  via `pane.get_columns()`, then mapped to an index with `_find_column_index`
  — this also lets a location without those columns (e.g. the Windows drives
  view) be skipped instead of raising.
- **Making the toggle apply live, without waiting for the next navigation:**
  `setColumnHidden(...)` resizes the section (to 0 when hiding, back to its
  old width when showing). Either resize fires the header's `sectionResized`
  signal, which `ResizeColumnsToContents._on_col_resized`
  (`src/main/python/fman/impl/view/resize_cols_to_contents.py`) is connected
  to. That handler then overwrites the width we just set with its own
  redistributed widths, undoing the show/hide — until the next navigation
  rebuilds the model and resets the handler's internal state, which is why
  it used to only work after moving to another folder.
  `_apply_column_visibility` fixes this in two steps:
  1. While calling `setColumnHidden(...)`, it sets
     `view._handle_col_resize = False` — the same reentrancy guard
     `_on_col_resized` already checks internally — so that one handler is
     suppressed for the toggle's own resize, without blocking the header's
     other Qt-internal signal handling (an earlier attempt using
     `header.blockSignals(True)` also suppressed those, which broke the
     "show" direction: the column's `isColumnHidden` flag flipped correctly,
     but nothing repainted it as visible again).
  2. It then calls `view.resizeColumnsToContents()` (the same public method
     already called after a folder loads, see `_on_location_loaded` in
     `src/main/python/fman/impl/widgets.py`) to force the remaining visible
     columns to relayout and fill the pane immediately — otherwise nothing
     triggers that relayout until the next real `resizeEvent` (e.g. the user
     resizing the window).
- `src/main/resources/base/Plugins/Core/core/tests/commands/test_columns.py`
  — `FindColumnIndexTest` covers the pure index-lookup logic, including the
  "column doesn't exist here" case. The live-relayout fix itself needs a real
  Qt view and isn't covered by a unit test.
- `src/main/python/fman/impl/view/fixed_column_widths.py` — selects stable
  content, sample, and dragged widths; its pure tests are in
  `src/unittest/python/fman_unittest/impl/view/test_fixed_column_widths.py`.
- `src/main/python/fman/impl/view/scrollbar_below_header.py` — positions the
  vertical scrollbar below the header.
- `src/unittest/python/fman_unittest/impl/view/column_widths_test.py` — covers
  sizing, persistence, reset/refit behavior, and scrollbar placement.
