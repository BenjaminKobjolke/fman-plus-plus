# Plugin API

How fman finds a plugin, what a plugin can extend, and the contracts each
extension point has to keep.

For installing, reloading and removing plugins - and what happens when two
of them ship a package of the same name - see
[`docs/PLUGINS.md`](PLUGINS.md).

Everything here is importable from `fman` (plus its sibling modules
`fman.fs`, `fman.url`, `fman.clipboard`). Anything under `fman.impl` is
internal: it changes without notice.

## Where plugins live

| Directory | What goes there |
|-----------|-----------------|
| `<resources>/Plugins` | The shipped **Core** plugin. Loads first. |
| `%APPDATA%\fman\Plugins\Third-party` | Installed plugins. |
| `%APPDATA%\fman\Plugins\User` | Your own. `User\Settings` always loads **last**, so its JSON wins. |

On macOS and Linux, `%APPDATA%\fman` is
`~/Library/Application Support/fman` and `~/.config/fman`. The path is
`fman.DATA_DIRECTORY` (`FMAN_DATA_DIRECTORY` overrides it).

`fman.APP_NAME` is the user-visible app name (`fman++`). `fman.FMAN_VERSION`
is the current app version.

Load order is shipped → third-party → user (`impl/plugins/discover.py`). Each
plugin directory is appended to `sys.path`, so a plugin can `import` any other
loaded plugin's packages — including Core's.

## Plugin layout

```
%APPDATA%\fman\Plugins\User\My Plugin\
    my_plugin\__init__.py                  <- required: a package
    *.ttf                                  <- fonts, loaded automatically
    Theme.css        / Theme (Windows).css
    Key Bindings.json / Key Bindings (Windows).json
    File Context Menu.json / Folder Context Menu.json
    <anything>.json                        <- read with load_json('<anything>.json')
```

Only **directories containing `__init__.py`** are imported
(`impl/plugins/plugin.py`, `_load_packages`). Loose `.py` files at the plugin
root are ignored, and so is a nested package that nothing re-exports — see
[Registration](#registration).

A `(Windows)` / `(Mac)` / `(Linux)` suffix on any JSON or CSS filename makes it
platform-specific; `fman.PLATFORM` is the same token.

## Registration

fman does not have a `register_*()` call. It **scans the classes** reachable
from each package's `__init__.py` namespace and registers anything whose
ancestry includes one of these:

| Base class | Gives you |
|------------|-----------|
| `ApplicationCommand` | A command in the palette, bound to the window |
| `DirectoryPaneCommand` | A command bound to the pane it ran from |
| `DirectoryPaneListener` | Callbacks for pane events |
| `fman.fs.FileSystem` | A new url scheme |
| `fman.fs.Column` | A new file-list column |
| `Viewer` | A file viewer shown inside a pane — see [Viewers](#viewers) |

Two consequences worth knowing:

- **Split your plugin across modules and you must re-export.** Only names
  reachable from `my_plugin/__init__.py` are scanned. Core does exactly this:
  `core/__init__.py` carries `from core.viewers import *` so the viewer classes
  in `core/viewers.py` are discovered.
- **Unloading is automatic.** Every registration pushes its own inverse action,
  which `fman.unload_plugin()` replays in reverse. Nothing you register leaks.

A command's name is its class name in snake_case: `CenterWindow` →
`center_window`. That is the name `Key Bindings.json` and `run_command()` use.

Set `usable_in_viewer = True` on a `DirectoryPaneCommand` to offer it in a
file viewer's palette and let its global shortcut work there. Set it only
when it acts on the viewed file, its folder, or the window layout; its result
is understandable while the file list is hidden; its key leaves viewer and
Qt keys free; and the viewer has no version of its own. The flag is inherited,
so subclasses that do not fit must set it back to `False`. A pane exposes the
registered opted-in names through `pane.get_viewer_commands()`.

## Commands run off the main thread

Commands and listeners run on a worker thread
(`impl/plugins/command_registry.py`). **Any Qt call must be wrapped**:

```python
from fman.impl.util.qt.thread import run_in_main_thread

class ShowSomething(DirectoryPaneCommand):
	@run_in_main_thread
	def __call__(self):
		...   # safe to touch widgets here
```

`fman.impl.util.qt.thread` is technically internal, but it is imported by a
dozen Core modules and is the sanctioned way to do this.

Exceptions inside a command are caught and reported rather than crashing fman.

## Console and plugin logging

`print()` output from plugins is captured in fman's console, while still being
forwarded to the original output stream when one exists. Plugins can also add
messages explicitly with `fman.log(*args)`, which joins the arguments with
spaces and appends a newline:

```python
import fman

fman.log('Finished loading', plugin_name)
```

Open the live console in a pane with **Show console**, or in a separate window
with **Show console window**. It includes a Python prompt for inspecting
`fman`, `window` and `pane`; entered code runs on a worker thread, like plugin
commands. Plugin failures appear in the console with their traceback. The
failure alert offers **Dismiss**, **Open in console** and **Copy error**.
See [The console](CONSOLE.md) for the entry formats and behavior.

## Panes

You receive a `DirectoryPane`; you never construct one. `self.pane` in a
`DirectoryPaneCommand`, `pane.window.get_panes()` for all of them. Panes are
addressed **by index** into that list — key bindings pass `pane_index`. The
"other pane" idiom is:

```python
panes = pane.window.get_panes()
other = panes[(panes.index(pane) + 1) % len(panes)]
```

There are two panes by default, but the count comes from the saved session, so
never assume exactly two.

### Pane activation

`DirectoryPaneListener.on_activated()` is called on a worker thread when the
pane receives keyboard focus. It is sent to listeners registered with that
pane. Keep Qt calls off this callback thread.

### Incognito mode

`fman.is_incognito()` returns whether incognito mode is currently enabled. The
setting lasts for the current fman session and is off again after a restart.
Plugins that record visited folders should skip adding visits to their history
while this returns `True`:

```python
import fman

if not fman.is_incognito():
	visited_folders.add(folder)
```

`DirectoryPaneListener.on_incognito_changed(enabled)` is called on a worker
thread each time the user turns the mode on or off. It is sent to listeners
registered with every open pane. Keep Qt calls off this callback thread, just
as with other listener callbacks. A plugin loaded while incognito is already
on does not receive an initial callback; query `fman.is_incognito()` when it
loads to learn the current state. When the mode turns off, fman then navigates
the panes back, so listeners receive the normal path-change callbacks after
`on_incognito_changed(False)`.

### Pane status messages

Use a pane's status methods for feedback that belongs to that pane. A message
appears in its own line and, by default, is also copied to the window-wide
[status bar](STATUSBAR.md). `timeout_secs` is optional; without it, the message
stays until replaced or cleared.

```python
self.pane.show_status_message('Copied 3 files', timeout_secs=3)
self.pane.clear_status_message()
```

`clear_status_message()` clears this pane's line. It also clears the window
status bar only if the bar still contains this pane's message, so it cannot
erase newer feedback. The commands **Toggle pane status lines** and **Toggle
pane messages in status bar** control these destinations; their saved settings
and theme support are described in the [status bar guide](STATUSBAR.md).

Plugins can change the pane count through the window:

| Method | Does |
|--------|------|
| `pane.window.add_pane()` | Appends and returns a `DirectoryPane`. Call `set_path()` to choose its folder; until then, it has no location to show. |
| `pane.window.remove_pane(pane)` | Removes a pane. Raises `ValueError` if it is the last pane or does not belong to this window. |

Removing a pane shifts the indices of panes to its right down by one. If your
plugin stores data by pane index, remove the deleted pane's entry yourself;
Core does this for its `Panes.json` settings. Listeners registered on a removed
pane receive no further events.

Location and selection: `get_path()`, `set_path(url, callback, onerror)`,
`reload()`, `get_selected_files()`, `get_file_under_cursor()`,
`place_cursor_at(url)`, `select()` / `deselect()`, `focus()`,
`get_columns()`, `get_sort_column()` / `set_sort_column()`.

## Putting your own widget in a pane

A pane can show **any `QWidget`** in place of its file list. This is what the
built-in file viewers are built on, and it is available to plugins directly —
your widget does not have to have a file behind it.

| Method | Does |
|--------|------|
| `pane.mount_widget(view, focus=True)` | Hides the file list, shows `view`, re-points the pane's focus proxy at it |
| `pane.unmount_widget()` | Removes and deletes it, restores the file list and its focus |
| `pane.get_mounted_widget()` | The mounted widget, or `None` |
| `pane.get_colors()` | `(background, foreground)` as hex, from the pane's live palette |

```python
from fman import DirectoryPaneCommand
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtWidgets import QLabel

class ShowHello(DirectoryPaneCommand):
	@run_in_main_thread
	def __call__(self):
		bg, fg = self.pane.get_colors()
		label = QLabel('hello')
		label.setStyleSheet(
			'QLabel { background-color: %s; color: %s; }' % (bg, fg)
		)
		self.pane.mount_widget(label)
```

Four things your widget owns once it is mounted:

- **Closing.** Nothing closes it for you. Handle `Escape` / `Enter` /
  `Backspace` in `keyPressEvent` and call `pane.unmount_widget()` — that is the
  contract users expect from the built-in viewers.
- **Pane switching.** `Tab` / `Shift+Tab` should run
  `pane.run_command('switch_panes')`. The focus proxy is already re-pointed, so
  tabbing back returns to your widget rather than the hidden file list.
- **Colors.** Use `get_colors()`. Hardcoding a palette means your widget is the
  one thing that ignores the user's theme.
- **Stylesheets.** Set colors with a **type-selector** rule
  (`QLabel { ... }`), never `*`. Core's `Theme.css` applies an app-wide
  `* { font-size: ...pt; }`, and once that touches a widget Qt switches it to
  the QSS style engine and stops honouring its palette. A local type rule beats
  the wildcard; a palette alone loses to it.

`focus=False` mounts without taking keyboard focus — for mounting into the
*other* pane while the user keeps browsing in this one.

## Viewers

A `Viewer` is a widget-in-a-pane that fman picks **for you**, by file, when the
user runs "View file". Subclass it and your viewer joins the built-in text,
image and video ones on equal footing — the viewer palette, next/previous-file
navigation and the per-viewer "advance only for same type" toggle all work
without further wiring.

For a custom viewer using `ViewerNavigator`, `actions()` supplies the opted-in
pane command palette rows. Call `run_pane_shortcut(key_event)` after your
viewer's own key handling and before `super().keyPressEvent(event)` so viewer
keys take priority.

```python
from fman import Viewer

class MarkdownViewer(Viewer):

	name = 'markdown'

	def matches(self, url):
		return url.lower().endswith('.md')

	def show(self, pane, url, focus_view=True):
		pane.mount_widget(build_my_widget(url), focus=focus_view)
```

| Member | Contract |
|--------|----------|
| `name` | **Required**, unique, stable. Also the navigation category and the key its settings are stored under (`<name>_viewer_advance_same_type` in `Core Settings.json`), so renaming it silently resets those. A viewer without a name is refused, with an error. |
| `priority` | Higher wins when two viewers match. Default `0`. |
| `matches(url)` | `True` if you handle this file. Called during directory scans too, so keep it cheap. |
| `show(pane, url, focus_view=True)` | Build the widget and mount it. Forward `focus_view` to `mount_widget`. |

### Priority, and why it exists

Registration order is plugin load order, and Core loads first. Core's text
viewer *sniffs* rather than matching an extension, so it says yes to any file
that is not an image, a video or a binary — including your `.md`. It therefore
sits at **`priority = -100`**, below the default, so plugin viewers get first
refusal. Leave `priority` alone unless you are deliberately overriding another
plugin.

### What fman guards for you

- A viewer whose `matches()` raises is **skipped**, not fatal: the error is
  reported and the next viewer is tried. One broken plugin cannot take "View
  file" down.
- Directories and non-local urls never reach a viewer — "View file" alerts on
  those instead (`core/viewers.py`, `viewer_for`).
- Unloading the plugin unregisters the viewer.

`fman.find_viewer(url)` returns the viewer that would handle a url, or `None`;
`fman.viewer_for_category(name)` looks one up by `name`. You rarely need
either — they exist for code that has to ask the question without opening
anything.

See [File viewers](viewers/FILE_VIEWERS.md) for the user-facing behaviour your
viewer inherits, and [Key bindings](KEYBINDINGS.md#viewer-specific-bindings)
for the viewer-scoped binding file.

## Settings and other JSON

`load_json('My Settings.json', default={})` merges that filename across
**every** plugin directory in load order — dicts update, lists prepend — so a
user file overrides yours. `save_json` writes only the difference, into
`User\Settings`.

Core exposes the one-key convenience both it and its viewers use:

```python
from core.settings import get_setting, save_setting
save_setting('My Settings.json', 'key', value)   # value=None clears the key
```

## Fonts

Any `*.ttf` in a plugin's root directory is loaded into Qt's font database when
the plugin loads, and unloaded with it. Reference it by the family name in the
font's own name table — not the filename. It also becomes selectable as the UI
font; see [Fonts](FONTS.md).

## Dialogs and progress

`show_alert`, `show_prompt`, `show_status_message`, `clear_status_message`,
`show_file_open_dialog`, `show_quicksearch` (with `QuicksearchItem`), and
`submit_task(Task(...))` for anything long enough to need a progress dialog.

A `FileSystem` can return more than 1 from
`get_parallel_transfers(src_url, dst_url)` to have Copy and Move transfer that
many files at once. The progress dialog then lists the workers, and the user
can add or remove them; `Task.show_workers(workers)` is how Copy asks for that
view. Set `task.blocks_later_tasks = True` on a task that later ones depend
on (creating a folder), and `task.waits_for_earlier_tasks = True` on one that
depends on all earlier ones (deleting an emptied folder). See
[Copy and Move](COPY_AND_MOVE.md#parallel-workers).

`show_quicksearch` returns `(query, value)`, or `None` if the user pressed
Escape. Pass `alt_accept=True` to also accept on **Shift+Enter**: the result is
then always a triple, `(query, value, alt)`, with `alt` telling the two apart.
Every other caller keeps the pair — see
[Command palette keywords](COMMAND_PALETTE_KEYWORDS.md) for what the palettes
do with it.
