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
`~/Library/Application Support/fman` and `~/.config/fman`. `fman.DATA_DIRECTORY`
selects the profile directory in this order:

1. `FMAN_DATA_DIRECTORY`, when set.
2. For a frozen Windows portable copy marked by `portable.txt`, the `Data` folder
   beside `fman.exe`.
3. The platform's default user data directory (`%APPDATA%\fman` on Windows,
   `~/Library/Application Support/fman` on macOS, or `~/.config/fman` on Linux).

The portable marker ships in the portable zip, not in the installer. See
[`PORTABLE.md`](PORTABLE.md) for details.

`fman.APP_NAME` is the user-visible app name (`fman++`). `fman.FMAN_VERSION`
is the current app version.

Load order is shipped → third-party → user (`impl/plugins/discover.py`). Each
plugin directory is appended to `sys.path`, so a plugin can `import` any other
loaded plugin's packages — including Core's.

The frozen app ships the full Python standard library except Tk and turtle,
IDLE, `lib2to3`, the test suite, `ensurepip` and `venv`. Third-party packages
still belong in the plugin's own folder.

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

When a pane has mixed file and folder sorting enabled, fman calls a column's
`get_mixed_sort_value(url, is_ascending)`. Its default delegates to
`get_sort_value`, so existing plugin columns keep their current order. A
column that sorts folders first can override it to remove that priority key.
See [mixed sorting](functions/mixed-sorting.md) for the built-in behavior.

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

## Opening files

Use `fman.fs.open(url, mode='r', encoding=None, errors=None, newline=None)` to
open a file through its registered file system. Text modes `'r'` and `'w'` use
the supplied text options; binary modes `'rb'` and `'wb'` read and write bytes.
The default mode is text read. The returned stream is a context manager:

```python
with fman.fs.open(url, 'r', encoding='utf-8') as stream:
	contents = stream.read()
	consume(contents)
```

A plugin that implements a `FileSystem` can provide `open(path, mode)` for
binary reads and writes. `path` is the file-system path without its URL scheme,
and the returned stream must support the corresponding read or write
operations and context manager. Text wrapping is handled by `fman.fs.open`, so
file systems only need to implement `'rb'` and `'wb'`. The base implementation
raises `NotImplementedError`, which keeps existing plugins compatible. The
streaming cross-file-system copy fallback and its requirements are described in
[Copy and Move](COPY_AND_MOVE.md#streaming-fallback-with-open).

## Choosing columns

`fman.fs` lets a plugin choose the columns shown by a file system, either as a
default for a URL scheme or for one folder. Column names are qualified names,
such as `core.Name` or `core.Size`, and must already be registered:

```python
import fman

# Use this default for local folders unless a folder has its own choice.
fman.fs.set_default_columns(
	'file://', ('core.Name', 'core.Size', 'core.Modified')
)

# Override the columns for this folder only. This choice survives restarts.
fman.fs.set_columns(
	'file:///Users/alex/Projects', ('core.Name', 'core.Modified')
)
```

The five functions are:

| Function | Effect |
|----------|--------|
| `fman.fs.get_columns(url)` | Returns the registered column objects selected for the folder. |
| `fman.fs.set_default_columns(scheme, column_names)` | Sets the in-memory default for a scheme such as `file://`. |
| `fman.fs.reset_default_columns(scheme)` | Removes that scheme's plugin default. |
| `fman.fs.set_columns(url, column_names)` | Saves a column choice for one folder in `Column Settings.json`. |
| `fman.fs.reset_columns(url)` | Removes that folder's saved choice. |

For a folder, fman uses its saved folder choice first, then the scheme default,
then the file system's own `get_default_columns()` result. A stored choice only
uses columns that are still registered, so a folder remains usable if a plugin
providing one of its columns is removed. An empty choice, or one with no
registered columns left, falls through to the next level. The scheme default
lasts for the session; folder choices are persisted across restarts.

Users control visibility separately from the column set. The column-header
menu lists every column except the first, and a user's hidden-column choice
continues to win if a plugin includes that column in its set. The first column
(normally `core.Name`) is always visible.

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

`pane.window.get_pane_sizes()` returns percentages in `get_panes()` order.
`pane.window.set_pane_sizes(sizes)` accepts one positive relative value per
pane; `[75, 25]` sets a 75/25 split and `[1, 1, 1]` sets three equal panes.
It raises `ValueError` when the list has the wrong number of values or contains
an invalid size. Hidden panes are reported as 0 by the getter.

### Editing a file name in place

`pane.edit_name(file_url, selection_start=0, selection_end=None, callback=None)`
opens the inline name editor. When `callback(file_url, new_name)` is supplied,
it runs on a worker thread after the user confirms the name. It does not run on
Escape, and it also runs when the name is unchanged. Exceptions are reported
like listener errors.

Without `callback`, the deprecated `DirectoryPaneListener.on_name_edited` event
is broadcast to every listener on the pane, and Core renames the file as before.
Listeners no longer receive `on_name_edited` for Core's own Rename command
(F2), because it now passes a callback.

### Pane activation

`DirectoryPaneListener.on_activated()` is called on a worker thread when the
pane receives keyboard focus. It is sent to listeners registered with that
pane. Keep Qt calls off this callback thread.

### Pane selection changes

`DirectoryPaneListener.on_selection_changed()` is called on a worker thread
after the selection changes. Rapid changes are combined into one callback
after a short debounce. A location change also has its usual
`on_path_changed()` callback; plugins should not rely on selection callbacks
for model resets.

### File shading

`pane.set_file_shading(shader, style='transparency')` applies a plugin-defined
shade to each file row. The shader receives a file URL and returns a number
from `0` (unchanged) to `1` (fully shaded), or `None` to leave that file
unchanged. Values are clamped to this range; an exception leaves the file
unchanged and its traceback is reported once for that shader. Pass `None` as
the shader to clear it. Supported styles are `transparency`, `tint`, and
`bold`; an unsupported style raises `ValueError`.

Selected files and the row under the cursor are not shaded. File shading itself
does not restrict URLs, but a shader should avoid slow work because it is
evaluated while the file list is drawn. The built-in age shader uses only local
files. This example assumes `fman` and `datetime` have been imported:

```python
def age_in_years(url):
	modified = fman.fs.query(url, 'modified_datetime')
	if modified is None: return None
	return min(1, max(0, (datetime.now(modified.tzinfo) - modified).days / 365))
pane.set_file_shading(age_in_years)
```

### File coloring

`pane.set_file_coloring(colorer)` sets the text color for each file URL. Return a
hex color or a color name from the active theme, or `None` to leave the file
unchanged. Pass `None` to clear the colorer. Selected files and the row under
the cursor keep their normal colors; hidden-file fading and file-age shading
still apply on top. Colorers run while the file list is drawn, so keep them
fast. For example:

```python
def color_images(url):
	if url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
		return '#e6db74'
	return None

pane.set_file_coloring(color_images)
```

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
self.pane.set_idle_status_message('3 files selected, 12.4 MB')
```

`clear_status_message()` clears this pane's line. It also clears the window
status bar only if the bar still contains this pane's message, so it cannot
erase newer feedback. The commands **Toggle pane status lines** and **Toggle
pane messages in status bar** control these destinations; their saved settings
and theme support are described in the [status bar guide](STATUSBAR.md).

`set_idle_status_message(text, pane_line=True, status_bar=False)` sets text
that appears whenever this pane has no active message. `pane_line` controls
the line below the pane's file list; `status_bar` controls the window bar while
this pane is focused. Set either destination to `False` to clear its idle text.
An active status message temporarily takes priority over idle text.

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
`get_chosen_files()`,
`place_cursor_at(url)`, `select()` / `deselect()`, `focus()`,
`get_columns()`, `get_sort_column()` / `set_sort_column()`.

`get_chosen_files()` returns the selected files, or the file under the cursor
when nothing is selected, or `[]` when neither is available.
`DirectoryPaneCommand.get_chosen_files()` remains available and returns the
same result.

## Putting your own widget in a pane

A pane can show **any `QWidget`** in place of its file list. This is what the
built-in file viewers are built on, and it is available to plugins directly —
your widget does not have to have a file behind it.

A mounted widget can also stand in for the pane's file list when commands ask
which item is current. Define `get_file_under_cursor()`,
`get_selected_files()`, `place_cursor_at(url)` and `get_location()` on the
widget to provide those values while it is mounted. `get_location()` supplies
`pane.get_path()`. Methods the widget does not define continue to use the file
list, so viewers that do not implement this protocol keep their existing
behavior. fman calls these methods on the main thread.

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

## Translations

Plugins can provide translations for their own commands, dialogs, and other
user-facing text. Add a `Translations` directory at the plugin root with one
JSON catalog per language:

```
My Plugin/
    Translations/
        en.json
        ru.json
```

Nested JSON keys use dot notation when looked up. The English catalog is the
fallback for a missing language or key. A translated catalog may omit a key
that exists in `en.json`:

```json
{
  "menu": {
    "open": "Open"
  }
}
```

The presence of at least one JSON file in `Translations` opts the plugin in;
fman discovers and unregisters its catalogs with the plugin lifecycle. Catalogs
are isolated by plugin name, which is the plugin directory's name. Use the
public `fman.translate(key, plugin_name)` function to look up plugin text:

```python
import fman

label = fman.translate('menu.open', 'My Plugin')
```

Built-in text can be looked up with `fman.translate(key)` and uses the selected
language with English fallback. A missing key is returned unchanged when neither
the plugin nor built-in English catalog defines it.

## Fonts

Any `*.ttf` in a plugin's root directory is loaded into Qt's font database when
the plugin loads, and unloaded with it. Reference it by the family name in the
font's own name table — not the filename. It also becomes selectable as the UI
font; see [Fonts](FONTS.md).

## Dialogs and progress

`show_input`, `show_alert`, `show_prompt`, `show_status_message`, `clear_status_message`,
`show_file_open_dialog`, `show_quicksearch` (with `QuicksearchItem`), and
`submit_task(Task(...))` for anything long enough to need a progress dialog.
`show_input(...)` returns the entered text, including an empty string, when the
user accepts, and `None` when they cancel. New code should use `show_input`;
`show_prompt(...)` still returns `(text, accepted)` for existing plugins.
`show_input(..., get_completions=f)` shows matching entries as the user types
and keeps Tab cycling through `f(text)`; the callback runs off the GUI thread.
The prompt message stays visible above the input. Arrow keys and clicks copy a
suggestion into the field, and Enter accepts exactly the text currently in it.

`fman.show_text_input(text, default='')` opens a multiline editor using fman's
input-dialog styling. Enter accepts the text; Shift+Enter inserts a line break.
It returns the accepted text, including an empty string, or `None` when the user
cancels.

```python
import fman

comment = fman.show_text_input('Comment', default='Existing note')
if comment is not None:
	save_comment(comment)
```

A `FileSystem` can return more than 1 from
`get_parallel_transfers(src_url, dst_url)` to have Copy and Move transfer that
many files at once. The progress dialog then lists the workers, and the user
can add or remove them; `Task.show_workers(workers)` is how Copy asks for that
view. A file system may also implement `get_connection_count(path)`, returning
the open connections it holds to the server behind that path, or `None` (the
default) when it has no such count. The multi-worker progress dialog then shows
`Threads: N · Connections: M`. This hook runs on the GUI thread on every
refresh and must only read in-memory state; an exception is treated as `None`.
A task returned by `prepare_copy(...)` or `prepare_move(...)` may be run again
after it fails, so it must be safe to run twice.
Set `task.blocks_later_tasks = True` on a task that later ones depend
on (creating a folder), and `task.waits_for_earlier_tasks = True` on one that
depends on all earlier ones (deleting an emptied folder). See
[Copy and Move](COPY_AND_MOVE.md#parallel-workers).

A `FileSystem` can return more than 1 from `get_parallel_deletes(path)` to
delete that many entries at once. Tasks with
`waits_for_earlier_tasks = True` start only after all earlier tasks finish and
hold back later tasks until they finish too.

Task subclasses can also set three class attributes to control their progress
window: `keeps_focus = True` makes it modal, `minimizable = True` adds a
minimize button, and `icon` supplies the optional `QIcon` shown in the status
bar while minimized. When no icon is set, fman uses its default icon. A task
that keeps focus cannot be minimized; tasks with neither option keep the
existing non-modal behavior.

Commands that perform file transfers can use
`fman.run_in_transfer_queue(title, fn)` to run their operation in the shared
Copy/Move/Robocopy queue. The call blocks the command's own thread until the
operation reaches the head, then runs `fn` and returns `True`. If the user
removes the waiting operation, it returns `False` without running `fn`.

```python
from fman import Task
from PyQt5.QtGui import QIcon

class DownloadTask(Task):
	minimizable = True
	icon = QIcon(':/my_plugin/download.png')
```

`show_quicksearch(..., title='')` can show a title above the input; the default
empty title keeps the header hidden. It returns `(query, value)`, or `None` if the user pressed
Escape. Pass `alt_accept=True` to also accept on **Shift+Enter**: the result is
then always a triple, `(query, value, alt)`, with `alt` telling the two apart.
Every other caller keeps the pair — see
[Command palette keywords](COMMAND_PALETTE_KEYWORDS.md) for what the palettes
do with it.
Pass `exit_keys` as a mapping of key bindings to command names to close the
dialog and switch commands. A value of `None` closes it like Escape; a command
name returns a `QuicksearchExit(query, command)` instead of the usual pair or
triple. This result is only returned by callers that pass `exit_keys`.
Pass `query_exit=f` to check each changed input string; when `f(text)` returns
a command name, the dialog closes with `QuicksearchExit(query, command, from_text=True)`.
`select_from` sets the start of the initial selection (default
`0`, which selects the full query); set it to the query length to place the
cursor at the end without selecting text. `QuicksearchExit.from_text` is
`False` for key-based exits and `True` for `query_exit` exits.
Pass `set_refresh=f` to receive a thread-safe function that re-runs `get_items`
for the current query text. Call it when asynchronous results arrive to update
the open list; calling it after the quicksearch dialog has closed does nothing.
