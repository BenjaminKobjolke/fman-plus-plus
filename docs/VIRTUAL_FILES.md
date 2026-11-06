# Windows virtual files

Some Windows applications offer files without creating them on disk. Outlook uses this format
for attachments and whole emails. fman reads every offered item and copies it into the active
pane; emails are saved as `.msg` files.

For paste, fman reads Windows' clipboard data object directly. For a drop, fman proxies the
native drop target Qt registered for the main window and keeps the source data object while the
drop is running. Qt reads the `FileContents` format only at index -1, which loses additional
items and does not handle storage-based `.msg` files. The proxy forwards the drop to Qt while
fman reads each virtual file by its index.

fman first saves items into a unique batch folder under the system temporary directory at
`fman virtual files`. The existing copy command then moves them into the pane, preserving its
normal confirmation, overwrite, progress, undo, and filesystem behavior. Batch folders older
than one day are pruned before a new batch is created; younger batches may still be in use by
an active copy.

If fman cannot install the native drop hook, drops keep their existing behavior. Paste support
still works because it reads the clipboard data object directly. Dragging files from fman into
an Outlook message is a separate issue and is not changed here.
