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
