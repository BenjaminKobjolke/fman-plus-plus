# Drag selection

Drag from the empty part of a file row to select a contiguous range. The gesture starts after the
pointer moves past Qt's drag distance, so a click by itself does not change the selection. Dragging
the file name still starts a file drag to another pane or app.

A plain drag clears the old selection and selects the rows from the starting row to the pointer.
Hold Ctrl while starting the drag to keep the old selection and add the range. On macOS, hold Cmd.
Move back toward the starting row to shrink the range.

When the pointer reaches the edge of the list, the view scrolls and extends the selection. This
also works in compact view, where the list scrolls horizontally.

Drag selection is on by default. Run **Toggle drag selection** in the command palette to turn it
off; dragging from the empty part of a row then drags the file as before. The choice is saved in
`%APPDATA%/fman/Local/Settings.json` under `drag_selection` and restored when fman starts.
