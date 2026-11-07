# Pane sizes

Set the width of each pane from the command palette or a plugin. Sizes are
specified for the whole window, so this works with any number of panes.

## Usage

Open the command palette and run **Set pane sizes**. Choose **Equal** or a
preset for the active pane: 25%, 33%, 67% or 75%. The remaining width is
shared evenly by the other panes. You can also run the command with an exact
list of sizes from a key binding or plugin.

Run **Widen active pane** or **Narrow active pane** to adjust the active
pane by 5 percentage points. Each command can take a `step` argument to use a
different number of percentage points. A pane will not become narrower than
10% through these commands.

## Commands

All three commands can be bound to keys in `Key Bindings.json`:

```json
{ "keys": ["Ctrl+Alt+7"], "command": "set_pane_sizes", "args": {"sizes": [75, 25]} }
{ "keys": ["Ctrl+Alt+Right"], "command": "widen_active_pane", "args": {"step": 10} }
```

`set_pane_sizes` with no `sizes` argument opens the preset picker. When a
`sizes` list is supplied, it sets those relative widths directly. Every list
must contain one positive number per pane. The commands are hidden when there
is only one pane or when any pane is hidden.

## Plugin API

`window.get_pane_sizes()` returns pane widths as percentages in
`window.get_panes()` order. A hidden pane has size 0. Use
`window.set_pane_sizes(sizes)` to set the whole layout; values are relative,
so `[75, 25]` sets a 75/25 split and `[1, 1, 1]` gives three equal panes.
The method raises `ValueError` if the list has the wrong number of entries or
contains a non-positive or non-numeric value.

Pane widths are part of the saved window state and are restored when fman
starts again.

## Implementation

- `src/main/python/fman/impl/pane_sizes.py` — validates and converts pane sizes.
- `src/main/python/fman/__init__.py` — public `Window` pane-size API.
- `src/main/python/fman/impl/widgets.py` — splitter width access.
- `src/main/resources/base/Plugins/Core/core/commands/pane_size.py` — Core
  commands and preset behavior.
- `src/main/resources/base/Plugins/Core/core/tests/commands/test_pane_size.py`
  — command tests.
- `src/unittest/python/fman_unittest/impl/test_pane_sizes.py` and
  `src/unittest/python/fman_unittest/test_window.py` — API tests.
