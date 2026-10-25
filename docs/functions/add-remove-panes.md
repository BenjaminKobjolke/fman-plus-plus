# Add and remove panes

Add file lists to the window or remove the active one. The pane count is
restored when fman starts again.

## Usage

1. Open the command palette and run **Add pane**. A new pane appears at the
   right, opens in the active pane's folder, and receives focus.
2. Run **Remove pane** to close the active pane. Focus moves to the next pane,
   wrapping to the first pane when the last one is removed.

## Commands

| Command | Shown when |
|---------|------------|
| Add pane | No pane is hidden |
| Remove pane | More than one pane exists and no pane is hidden |

Both commands can be bound to keys in `Key Bindings.json`. Neither has a
default key binding.

## Notes

- There is always at least one pane. Add pane appends at the right end.
- The pane count persists across restarts.
- While a pane is hidden with **Show only active pane**, both commands are
  hidden until **Show all panes** restores the layout.
- Copy and move commands still work with one pane; their destination prompt
  starts with the current folder, which you can edit.
- **Open in left pane** and **Open in right pane** are hidden with one pane.
  `Alt+F2` shows volumes in the only pane. `Tab` has no other visible pane to
  focus.

## Implementation

- `src/main/resources/base/Plugins/Core/core/commands/pane_view.py` — palette
  commands and pane visibility rules.
- `src/main/python/fman/__init__.py` — `Window.add_pane()` and
  `Window.remove_pane()` plugin API.
- `src/main/python/fman/impl/session.py` — saves and restores the pane count.
- `src/main/resources/base/Plugins/Core/core/commands/hidden_files.py` —
  removes index-based hidden-file settings when a pane closes.
