# Copy and Move

How fman's built-in Copy (F5) and Move (F6) find the files to transfer and
transfer them, why the two run at the same time, and how a file system such as
FTP gets several files transferred at once.

Both commands are `FileTreeOperation` subclasses (`CopyFiles`, `MoveFiles`) in
`src/main/resources/base/Plugins/Core/core/fileoperations.py`; the tree
gathering methods are in `core/file_tree_gathering.py`. The robocopy variants
are separate and described in [ROBOCOPY.md](ROBOCOPY.md).

Core copy and move progress dialogs can be minimized with `–` and restored
from their status bar icon.

## Two threads: gathering and transferring

Copying a folder means walking the tree first: which files are there, does the
destination already hold one of them, how big is each. On a local drive that
is quick. On a remote file system, an FTP server for example, every folder
costs a round trip, and a large tree can take minutes to walk.

fman used to finish that walk before transferring anything. The progress
dialog sat on "Gathering files..." and then "Preparing to copy N files" while
nothing moved.

Now the walk runs on its own thread and transfers start as soon as the first
file is found:

```
gathering thread                       transferring thread
----------------                       -------------------
_gather_files()                        _run_gathered_tasks()
  checks, makedirs(destination)          queue.get() ──► run task
  per source: prepare_copy(...) ──►      queue.get() ──► run task
    overwrite prompt if needed  queue    ...
  ...                                    _DONE ──► finished
  queue.put(_DONE)
```

- **The gathering thread** (`_gather_in_background`) runs the same
  `_gather_files()` as before. `_enqueue(...)` puts each task on a `Queue` the
  moment the file system yields it, instead of collecting them in a list.
- **The transferring thread** is the command's own worker thread. It takes
  tasks off the queue and runs them with the same error handling as before.
- **`_DONE`** always ends the queue, however the gathering stopped: done,
  canceled, aborted or crashed. An exception raised while gathering is stored
  and raised again once the transfers have ended.

## Details that follow from it

- **The progress bar total grows.** Nobody knows the total size while the walk
  is still running, so each task's size is added to the total when it starts.
  The bar still ends at 100%.
- **One task of look-ahead.** Before running a task, the transferring thread
  waits until the queue holds its next item, without taking it. That is how
  it knows a failing task is the last one, which decides whether the error
  prompt offers `OK` or `Yes / Yes to all / Abort`.
- **One prompt at a time.** Overwrite prompts come from the gathering thread,
  error prompts from the transferring one. Without a lock the second modal
  dialog would open inside the first's event loop. `_alert_lock` is held
  around both `_should_overwrite(...)` and `_handle_exception(...)`.
- **Stopping.** Cancel is seen by both threads. When the transfers end early
  (Abort on an error prompt), `_stop_gathering` makes `_iter(...)` stop the
  walk, and the transferring thread waits for the gathering thread before it
  returns.
- **Abort on an overwrite prompt** stops the queued tasks that have not started
  yet. Files transferred before that point stay transferred, the same as an
  Abort on an error prompt mid-copy.

## Overwrite prompts

When a file destination already exists, Copy and Move show its size and modified
date beside the incoming file's values. On local `.exe` and `.dll` files on
Windows, the dialog also shows available program versions. It marks the newer
date with `(newer)` and the larger size with `(larger)`; equal values are not
marked. Missing or unreadable details are left blank.

The dialog uses two button rows to keep all choices visible: **Overwrite**,
**Overwrite all**, **Rename**, and **Rename all** on the first row; **Skip**,
**Skip all**, and **Abort** on the second. Overwrite is the default choice.

**Rename** keeps both files and asks for a new name, prefilled with an available
name such as `report (2).txt`. **Rename all** uses the same numbered naming
pattern automatically for later file conflicts in that operation. Existing
files and names already chosen during the operation count as taken, so the
number increases until a free name is found. Folder conflicts continue to merge
their contents without prompting. Undo also tracks renamed top-level files, so
undoing a copy or move removes the renamed destination.

## When a move stops halfway

Core automatically moves completed local files back to their original
locations when you cancel a move, choose Abort on an overwrite or error prompt,
or an unexpected error stops the operation. An error on the last file also
counts as stopping: its prompt only offers OK, so there is no way to continue.
If a source location has been filled again before rollback reaches it, Core
leaves that moved file at the destination and reports the paths it could not
restore. The alert lists up to ten paths and gives the count of any remaining
ones. A destination file replaced with your approval cannot be recovered by
rolling the moved file back.

This rollback applies to local file-system moves. Plugin file systems can opt
in by marking their move tasks with the same rollback data; other plugins and
moves run in an elevated process do not roll back. When a local move does roll
back, it removes only empty folders created under its new destination, and
keeps pre-existing folders and any files another process placed there.

Local copies and moves that copy across drives write regular files to a
temporary `.fman-partial` name beside the destination, then publish the final
name only after the copy and metadata update succeed. A failed or canceled copy
removes the temporary file and preserves any old destination file until that
publish. Symlinks keep their existing handling.

Before a local file is moved across drives or replaces an existing copy
destination, Core checks whether another program has it open. This happens
right before each file so large folder operations do not need a slow up-front
scan. The check is on by default on Windows; use the **Toggle locked file
check** command to turn it off or back on. Its setting key is
`check_locked_files` in `Core Settings.json`. Other platforms skip the check.

Overwrite details are shown by default. Set `show_overwrite_details` in
`Core Settings.json` to `false` to show only the overwrite question and buttons;
use the **Toggle overwrite details** command in the command palette to switch
details off or back on.

## Selection after a copy

When Copy is started from the source pane's selection, each top-level item is
deselected after all of its transfer tasks succeed. A folder stays selected
when any file inside it is skipped, fails, is canceled or is not reached; the
same applies to individual files that do not arrive. This is enabled by
default. Use **Toggle deselect after copy** to switch it off or back on; the
setting is `deselect_after_transfer` in `Core Settings.json`.

Drag-and-drop, clipboard paste and elevated copies leave pane selection alone.
Moves need no selection update: successful items leave the source pane, while
items restored after a stopped move remain unselected as before.

## Parallel workers

A file system can ask for several transferring threads: Copy and Move ask
`fman.fs.get_parallel_transfers(src, dest)`, which takes the larger answer of
the source and destination file system. The base `FileSystem` answers 1. The
FTP plugin answers 3 between FTP and this machine, so downloads and uploads run
three files at once, each on its own connection. Its moves go file by file:
each source file is deleted right after its own copy, and an emptied source
folder last.

The progress dialog shows the worker count and, when available, the total
connection count for the source and destination servers. It asks a server only
once when both URLs point to it, and shows `Threads: N` alone when every
connection count is unknown.

`TransferWorkers` (`core/transfer_workers.py`) runs the queue:

- **One worker runs on the command's thread**, exactly as before. Several
  run on threads of their own, and the progress dialog lists them: one line
  per worker with its file and percentage, and `−` / `+` buttons
  (`Task.show_workers(...)`, drawn by `fman/impl/workers_label.py`).
- **`+`** starts another worker, up to 10. **`−`** marks the newest worker
  retiring: it finishes its active file and then stops. A worker that was
  waiting for a file runs the one it gets, then stops. At least one worker
  always stays.
- **`_DONE` stays in the queue.** A worker that draws it puts it back, so
  every worker sees it.
- **The look-ahead does not take the next task**, since another worker may
  run it. With several workers, "last" means nothing more is queued yet. If
  several workers wait on the queue, one `put(...)` wakes only one of them, so
  a worker that wakes passes the wakeup on.
- **Progress is added, not set.** `ChildProgressDialog` sets the parent's
  progress absolutely, which parallel tasks would overwrite. Each task runs
  with a `WorkerProgress` that adds its change instead, under
  `_progress_lock`. The GUI thread never takes that lock, because
  `set_size(...)` waits for the GUI thread while holding it.
- **An Abort or an error in one worker stops all of them** before their next
  task, and also stops the walk, which the other workers would otherwise wait
  for.
- **Order where it matters.** Queue order alone means nothing to N workers, so
  two `Task` flags restore it:
  - `blocks_later_tasks`, set on "Creating a folder": later tasks, such as the
    files that go into the folder, do not start until it is done.
  - `waits_for_earlier_tasks`, set on "Deleting an emptied folder" (plugin and
    `MoveFiles._postprocess_directory`): the task starts once every earlier
    task is done. It also blocks later tasks.

  `_take()` numbers each task while the queue is still locked, so the numbers
  follow the queue's order however the workers race. A task then waits only
  for unfinished earlier numbers. A barrier task waits for all of them, any
  other task only for the blocking ones.

## What a file system plugin has to do

Streaming only helps if `prepare_copy(...)` hands tasks out one at a time. Return
a generator, not a list:

```python
def prepare_copy(self, src_url, dst_url):
	# Raise here, not on the first iteration: fman tries the other file
	# system only when this call itself raises UnsupportedOperation.
	if not self._can_copy(src_url, dst_url):
		raise UnsupportedOperation
	return self._prepare_copy(src_url, dst_url)

def _prepare_copy(self, src_url, dst_url):
	if not self.is_dir(src_url):
		yield CopyFile(...)
		return
	yield Task('Creating ...', fn=self.mkdir, ...)
	for name in self.iterdir(src_url):
		yield from self._prepare_copy(join(src_url, name), join(dst_url, name))
```

`LocalFileSystem` (`core/fs/local/__init__.py`) uses the transfer methods in
`core/fs/local/transfers.py`; the FTP plugin also works this way. A plugin that
returns a list still works, just without streaming for that folder. The same
goes for `prepare_move(...)`.

To have its transfers run on several workers, a plugin also:

- returns more than 1 from `get_parallel_transfers(src_url, dst_url)`;
- may return its open connections from `get_connection_count(path)`;
- marks a task that later tasks depend on, typically creating a folder, with
  `task.blocks_later_tasks = True`;
- marks a task that depends on all earlier ones, typically deleting a folder a
  move has emptied, with `task.waits_for_earlier_tasks = True`.

Everything else may run in any order, so a move should yield one task per
file (copy, then delete that source file) rather than one task for the whole
tree. The FTP plugin's `_prepare_move` does exactly that:

```python
def _prepare_move(self, src_url, dst_url):
	if not fs.is_dir(src_url):
		yield _Sequence('Moving ...', [copy_task, delete_source_task])
		return
	yield self._prepare_mkdir(dst_url)          # blocks_later_tasks
	for name in fs.iterdir(src_url):
		yield from self._prepare_move(join(src_url, name), join(dst_url, name))
	yield delete_if_empty_task                  # waits_for_earlier_tasks
```

Both flags are class attributes of `fman.Task`, set on the instance, so the
plugin still loads in an fman without them. Such an fman runs one worker, and
there the queue order is enough.

`prepare_copy(...)` is now called from the gathering thread, and the tasks run
on other threads. A plugin that keeps connections per thread opens one for the
walk and one per worker. The FTP plugin does this, so a server that limits
connections per IP may refuse some. The user can press `−` in the progress
dialog.

## Tests

`core/tests/test_fileoperations.py` covers overwrite and error prompts, abort
and move-to-self. `core/tests/test_parallel_transfers.py` contains
`StreamingTransferTest` and `ParallelTransferTest`. `StreamingTransferTest`
checks that a transfer starts while gathering is still running: its file
system's `iterdir(...)` waits until a copy has started, and gives up after
5 seconds, so a sequential version fails the test instead of hanging the run.
`ParallelTransferTest` does the same for workers: each copy or move waits until
all of them have started. It also checks that Move's emptied-folder task waits
for the earlier tasks.
`core/tests/test_transfer_workers.py` covers adding, removing, aborting,
errors, and the two ordering flags. A barrier task starts only after the
earlier tasks end. A blocking task starts without waiting for earlier ones,
but holds back the later ones.

`core/tests/test_transfer_completion.py` covers per-item completion across
parallel tasks and skipped or failed work.

The FTP plugin's side is checked by its own scripts, without fman running:
`test_copy_single_dialog.py` covers the per-file move tasks, the flags, the
folder delete that keeps a non-empty folder, and `get_parallel_transfers`.

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_core_tests.bat'"
```

The worker rows and buttons are tested in
`fman_unittest/impl/progress_dialog_test.py`, via
`tools\run_progress_dialog_tests.bat`.
