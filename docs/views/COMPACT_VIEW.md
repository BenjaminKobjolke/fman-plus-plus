# Compact view

Compact view shows only file names in several columns, like the Brief view in
Total Commander. Each pane has its own mode, and fman restores the mode when it
reopens the session.

To switch the active pane, open the command palette and run **Toggle compact
view**. There is no default keyboard shortcut; you can assign one in the key
bindings settings.

Names fill each column from top to bottom, then continue in the next column.
All columns use the width of the longest name, up to the pane width. Longer
names end in an ellipsis; hover over one to see its full name. File icons remain
visible.

Sorting uses the existing sort commands and key bindings. Compact view has no
column header, so choose a sort from the command palette or use its key binding.
The usual selection, rename, copy, move, open, drag-and-drop and context-menu
commands remain available. Left and Right continue through their configured key
bindings; without a binding, the list uses Qt's previous/next-column movement.
