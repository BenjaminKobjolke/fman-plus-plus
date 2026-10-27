# The tutorial

fman's onboarding tour: the little speech bubble that walks a new user through
GoTo, the Command Palette and the two panes.

It starts by itself on the first run, in the left pane
(`ApplicationContext.on_main_window_shown`), and is skipped while a demo is
being recorded. Afterwards it can be started again from the Command Palette
(`Ctrl+Shift+P` → **Tutorial**), and on macOS from the **Help** menu. If a
first-run user aborts the tour and then reaches for the mouse, `UsageHelper`
offers it once more.

A second tour, **Cleanup guide**, uses the same machinery to walk the user
through tidying a folder.

The tour is meant to teach the keyboard. That only works if the tour itself can
be driven from the keyboard, and if it stays out of the way of the file list it
is talking about — which is what most of this document is about.

## Where the bubble sits

Bottom right of the window, with a 20 px margin, above the status bar when that
is shown.

It used to be centered — directly on top of the rows the step was asking the
user to navigate. The bottom right corner is the one part of a two-pane window
that is reliably empty.

The position is deliberately **stable**: the bubble does not follow the cursor,
the active pane, or a dialog. It moves in exactly one case — when an open
dialog's rectangle would overlap it, it hops to just **above** that dialog,
still right-aligned. Raising the overlay is not an option there: `Quicksearch`
(the Command Palette, GoTo, …) is a `QDialog`, a top-level window of its own,
so it always paints over a child widget of the main window regardless of
z-order.

Above the dialog, not simply at the top margin: the Command Palette is centered
and tall, so it reaches into the top right corner too — a bubble that jumped
there landed right on it, which is the bug this rule replaced.

The result is clamped to `(0, 0)`: an overlay larger than the window, or one
that a dialog leaves no room above, keeps its title and the start of its text
visible instead of scrolling off the top left. In the second case it still
overlaps the dialog — there is nowhere left to put it.

## Who owns the keyboard

Every step declares whether its bubble takes focus. This is the whole design:

| Step asks the user to… | `takes_focus` | Keyboard goes to |
|---|---|---|
| …press a key in the pane ("press *Tab*", "press *F5*", "type its name") | `False` | the directory pane |
| …acknowledge and move on ("Yes"/"No", "Continue", "Close") | `True` | the bubble's buttons |

`TourStep` defaults to `bool(buttons)` — a step with buttons and nothing else
to do takes focus. Steps that show a button *and* expect pane input pass
`takes_focus=False` explicitly. There are three of them:

- the tutorial's copy/move step ("press *Tab* … press *F5* … then click the
  button below") — Enter there belongs to fman's copy and delete confirmation
  dialogs, not to the bubble;
- the cleanup guide's two "navigate to a folder, then click Next" steps.

Getting this wrong is not cosmetic. fman dispatches its key bindings from the
directory pane's key handler (`FileListView.keyPressEvent` →
`key_press_event_filter`), so while a bubble button holds focus, fman's
shortcuts do not fire at all. That is fine — and only fine — on a step where
there is nothing left to do but continue.

While a bubble holds focus, the pane's cursor row loses its highlight
(`SingleRowModeDelegate._should_draw_cursor` only draws it for a focused view).
It comes back when the step closes and focus is handed back.

## Driving a focused bubble

- **Enter** activates the focused button. Every button gets
  `setAutoDefault(True)`: outside a `QDialog`, `QPushButton` ignores Enter
  unless `autoDefault` is set explicitly, so without this only clicking would
  work. Qt also paints the focused button as the default one, which is how the
  user sees where Enter would go.
- **Arrow keys** move between the buttons — Left/Up back, Right/Down forward,
  wrapping around. Qt only moves focus with Tab/Backtab on the desktop, and
  `MainWindow.focusNextPrevChild(...)` returns `False` so that fman can use Tab
  to switch panes. So `Overlay` moves the focus itself, from an event filter
  installed on its buttons.
- **Alt+letter** activates a button wherever focus is. Button labels carry a
  mnemonic (`'&Yes'`, `'&No'`, `'&Continue'`), which Qt turns into an
  `Alt+<letter>` shortcut. No `Alt+<letter>` key binding exists in fman's
  `Key Bindings*.json` (only `Alt+Arrow`, `Alt+F1/F2/F5`, `Alt+Enter`), so
  there is nothing to collide with.
- The **last** button is the affirmative one by convention (`[('&No', …),
  ('&Yes', …)]`) and is the one focused when the step opens.

When the step closes, focus goes back to the widget that had it before the
bubble appeared — normally the directory pane, so the next step's instructions
("press *Tab*", "type its name") land where the user expects.

## Writing a step

A `TourStep` is a title, a list of paragraphs, optional command actions and
optional buttons:

```python
TourStep(
    'Great Work!',
    [
        "You've completed the tutorial. Remember:",
        "* *Ctrl+P* lets you go to any _P_ath.",
    ],
    buttons=[('&Close', self.complete)]
)
```

Paragraph markup, rendered by `TourStep._get_body_html`:

| Syntax | Result |
|---|---|
| `*text*` | highlighted (`fman.impl.html_style.highlight`) |
| `_text_` | underlined |
| `* item` at the start of a line | list item; consecutive ones become one `<ul>` |
| anything else | a `<p>` |

Paragraphs also go through `%`-formatting via `Tour._format_next_step_paragraph`
when a step needs a value the previous step produced (a folder name, a number
of seconds).

A step advances when the user presses a button, or when a `command_actions`
hook fires:

```python
TourStep(
    '', ["Press *Ctrl+P* to launch GoTo!"],
    {'before': {'GoTo': self._after_dialog_shown(self._before_goto)}}
)
```

- `'before'` / `'after'` — keyed by command name, fired by the command callback
  around that command running.
- The GoTo step's text is chosen in `Tutorial._before_goto`: when the target is
  the user's home directory it teaches **both** ways to type it — `~`, or
  `home`, which matches because GoTo labels its well-known directories (see
  [`docs/functions/go-to.md`](functions/go-to.md)). Keep that sentence in step
  with `get_well_known_dirs()` in `Plugins/Core/core/commands/util.py`: if a
  name there ever changes, the tutorial is telling the user to type something
  that no longer matches.
- Both alternatives it offers must be things the user does **inside the
  dialog**. The step is gated on `{'before': {'GoTo': …}}`, so it only advances
  when the `go_to` command runs — naming another route to the same folder (the
  `go_home` palette command, say) would strand a user who took it on a step
  that never completes.
- `'on': {'location_changed': …}` — fired when the tour's pane navigates.
- `Tour._after_dialog_shown(callback)` defers a callback until the dialog a
  command opened is actually on screen. A `'before'` hook fires before the
  command runs, so without it the next step's bubble would be built while the
  dialog it talks about does not exist yet — and its placement could not tell
  whether the two would overlap.

## Implementation

- `src/main/python/fman/impl/onboarding/__init__.py` — `Tour` (step sequencing,
  command/location listeners, metrics), `TourStep` (one screen: HTML,
  `takes_focus`, command actions), `TourController`, `AfterDialogShown`.
- `src/main/python/fman/impl/onboarding/tutorial.py` — the tutorial's steps and
  its navigation coaching. `_get_navigation_steps(...)` computes the sequence
  of `open` / `go up` / `show drives` / `toggle hidden files` / `go to` moves
  from where the user is to the folder they picked, and `_navigate()` rewrites
  the current step's text after each one.
- `src/main/python/fman/impl/onboarding/cleanup_guide.py` — the cleanup tour.
- `src/main/python/fman/impl/overlay.py` — `Overlay` (the bubble: buttons,
  focus, arrow keys).
- `src/main/python/fman/impl/widgets.py` — `MainWindow._position_overlay` /
  `_overlay_pos(...)` / `_dialog_rect()` (where it goes). `_overlay_pos(...)`
  is a free function over plain sizes and rects, so the placement rules are
  testable without a window.
- `src/main/python/fman/impl/plugins/builtin.py` — registers the `Tutorial` and
  `CleanupGuide` pane commands, which is what puts them in the Command Palette.
- `src/main/python/fman/impl/application_context.py` — `tutorial_factory`,
  `cleanupguide_factory`, `tour_controller`.

## Tests

```bash
tools\run_window_chrome_tests.bat   # placement rules (fman_unittest.impl.test_widgets)
tools\run_overlay_focus_tests.bat   # focus, arrow keys, Enter, mnemonics
```

`overlay_focus_test.py` is named that way on purpose: it needs a `QApplication`
of its own, and `python build.py test` discovers `test*.py`, so the name keeps
it out of that suite — leftover Qt state is what makes it hang (see
`CLAUDE.md`). It runs offscreen, so no window appears. Same trick as
`core/tests/fs/zip_test.py`.

`fman_unittest.impl.onboarding.test_tutorial` covers `_get_navigation_steps`
and runs under `python build.py test`.
