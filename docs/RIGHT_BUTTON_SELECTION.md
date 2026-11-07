# Right-button selection

Right-button selection lets you mark files with the right mouse button, like in Total Commander.
It is off by default, so right-click continues to open the context menu until you enable the mode.

Open the command palette and run **Toggle right-button selection** to turn the mode on or off. The
choice is saved in `%APPDATA%/fman/Local/Settings.json` under `right_button_selection` and is
restored when fman starts. When the mode is on, right-click a file to mark or unmark it. Drag the
right button over rows to apply the state of the starting file to each row passed over.

Hold the right button on a file for one second to open the context menu for the selected files.
Right-clicking empty space and opening the menu with the keyboard still open it immediately. A
left-button drag continues to drag files to another pane.

Right-button dragging does not scroll the list automatically when the pointer reaches its top or
bottom edge.
