# Sort arrow placement

The sort arrow appears beside the sorted column's label by default, for example
`Name ▲`. This keeps it visually associated with the column even when the column
is wide.

Set `sort_arrow_position` in `%APPDATA%/fman/Local/Settings.json` to choose a
placement:

| Value | Placement |
| --- | --- |
| `after` | After the label (default) |
| `before` | Before the label |
| `edge` | At the right edge of the column, as in earlier versions |

Restart fman after changing the setting. If the label and arrow do not fit
side by side in a narrow column, the arrow stays at the column's right edge so
it does not overlap the label.

A custom theme that defines `QHeaderView::up-arrow` or
`QHeaderView::down-arrow` draws its own arrow, so this setting does not affect
the arrow in that theme.
