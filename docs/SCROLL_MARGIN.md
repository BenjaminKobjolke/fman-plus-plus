# Scroll margin

The scroll margin keeps a chosen number of rows visible above and below the
keyboard cursor in the file list. This gives you more context while moving or
selecting files with the keyboard. Near the first or last file, the margin
shrinks so the cursor can reach the end of the list. Mouse clicks do not move
the list.

Set `scroll_margin` in `%APPDATA%/fman/Local/Settings.json`:

```json
{
  "scroll_margin": 3
}
```

The default is `0`, which turns the margin off. Larger values keep the cursor
near the middle of the visible list. Invalid values count as `0`. Restart fman
after changing this setting.
