# File comments

fman stores comments for files and folders in a `descript.ion` file in the same
directory. The format is compatible with Total Commander, so both applications
can read and update the same comments.

## Editing comments

Select one or more files or folders and press **Ctrl+Shift+Z** on Windows or
Linux, or **Cmd+Shift+Z** on macOS. If nothing is selected, fman edits the item
under the cursor. The editor starts with a comment only when every chosen item
has the same comment. **Enter** saves and **Shift+Enter** inserts a new line.
Saving an empty comment removes it.

## Format and encodings

Each directory has one `descript.ion`; its entries name the files and folders
in that directory. Names containing spaces are quoted. Line breaks inside a
comment are represented by `\n`, followed by the multi-line marker `\x04Â`.
fman writes CRLF line endings and preserves entries it does not recognize.

When reading, fman accepts UTF-8 with a byte-order mark, plain UTF-8, and then
the system ANSI encoding (Windows) or Latin-1 (macOS and Linux). Existing files
keep their encoding when possible. New files use UTF-8 with a byte-order mark;
if a comment cannot be represented in an existing encoding, fman switches that
file to UTF-8 with a byte-order mark.

## Comment column

The Comment column is included by default. It is shown in directories that
contain comments and hidden automatically in directories without any. It shows
the first line of each comment. Use the column header menu or **Toggle comment
column** to hide or show the column; a manual visibility choice applies across
directories.

After copying or moving a comment into a directory that has no comments yet,
the column appears when that directory is next visited or refreshed. Saving a
comment in the editor updates its visibility immediately.

## Supported locations and file operations

Comments are supported for local `file://` locations. Other URL schemes, such
as archive and FTP locations, and network roots are not supported.

Comments follow files and folders when they are copied, moved or renamed.
Successful trash and permanent deletion remove the comment. Undo restores
comments for trashed items and moves comments back with files restored from a
move or rename. A problem reading or writing `descript.ion` is reported in the
status bar and does not change the result of the file operation.
