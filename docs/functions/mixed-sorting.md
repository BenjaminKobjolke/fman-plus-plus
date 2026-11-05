# Mix files and folders while sorting

Use **Toggle mixed file and folder sorting** in the command palette to change
the current pane. The other pane keeps its own choice. Each pane's preference
is saved in `Panes.json` and restored when fman starts.

When mixed sorting is on, files and folders are ordered together in every
column: Name, Size, Modified, Extension, Version and Attributes. For Size,
folders count as size zero and are ordered by name alongside empty files.

Plugin columns keep their existing sort behavior by default. A plugin can
override `Column.get_mixed_sort_value(url, is_ascending)` to choose how its
values are ordered when the pane mixes files and folders.
