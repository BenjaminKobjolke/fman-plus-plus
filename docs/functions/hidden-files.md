# Toggle hidden files

Use **Toggle hidden files** (`Ctrl+.`) to show or hide dotfiles and files that
Windows marks as hidden. When shown, hidden entries have gray icons and paler
names; hidden folders remain brighter than hidden files. Selection keeps its
usual color, and the entries can still be selected, renamed and dragged.

## Disable the faded look

Set `"dim_hidden_files": false` in `Core Settings.json` to show hidden entries
with their normal text and icons. The setting defaults to `true`. It takes
effect the next time you toggle hidden files, reload Core, or restart fman.

Themes can customize the faded text colors with `pane_hidden_fg` and
`pane_hidden_fg_dir`; see [Themes](../THEMES.md#derived-tokens).

## Hide or unhide files

On Windows, use **Set hidden attribute** or **Remove hidden attribute** in the
command palette to mark or unmark the selected files. If nothing is selected,
the command acts on the file under the cursor. These commands only change the
Windows hidden attribute; they do not move, rename or delete files. Open panes
show the change after refreshing, and an alert names any files fman could not
change, such as files in protected folders where fman cannot request admin
rights.
