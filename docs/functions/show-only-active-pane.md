# Show only active pane

Command palette entry that collapses fman's dual-pane layout down to just the
active pane, and a second entry to restore the normal split view.

## Usage

1. Open the command palette (default shortcut varies by platform).
2. Run **"Show only active pane"** — the inactive pane is hidden, the active
   pane fills the window, and focus stays on the active pane.
3. Open the palette again — the entry is now labeled **"Show all panes"**.
   Run it to restore the normal two-pane split.

Only one of the two entries is shown at a time; which one depends on the
current pane visibility, not on a saved setting.

## Commands

| Command name             | Palette label              | Shown when                  |
|---------------------------|-----------------------------|------------------------------|
| `show_only_active_pane`   | Show only active pane        | 2+ panes exist, all visible  |
| `show_all_panes`          | Show all panes                | at least one pane is hidden  |

Both can be bound to a key in `Key Bindings.json` like any other command,
e.g.:

```json
{ "keys": ["Ctrl+Alt+O"], "command": "show_only_active_pane" },
{ "keys": ["Ctrl+Alt+O"], "command": "show_all_panes" }
```

No default key binding is set — the feature is palette-only.

## Notes

- State is not persisted: closing and reopening fman always starts with all
  panes visible.
- With only a single pane open, "Show only active pane" does not appear
  (there is nothing to collapse).
- While a pane is hidden, `switch_panes` (`Tab`) does nothing — it would
  otherwise move the cursor into the pane you can't see.
- "Add pane" and "Remove pane" are hidden from the palette until all panes are
  visible again.

## Implementation

- `src/main/resources/base/Plugins/Core/core/commands/pane_view.py` —
  `ShowOnlyActivePane` and `ShowAllPanes` (`DirectoryPaneCommand` subclasses).
  Each pane's Qt widget visibility (`pane._widget.setVisible(...)`) is toggled
  directly; the `QSplitter` that holds the panes redistributes space
  automatically. `is_visible()` on each command determines which one the
  palette offers, based on current pane visibility — not a static label.
- `src/main/resources/base/Plugins/Core/core/tests/commands/test_pane_view.py` —
  `ShowOnlyActivePaneTest`, `ShowAllPanesTest`.
