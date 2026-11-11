# fman command in PATH

On Windows, the **Toggle fman command in PATH** command palette entry adds or
removes the current fman's `bin` folder from your user PATH. After adding it,
open a new terminal before typing `fman`.

The Windows installer adds fman to PATH automatically. If you remove it with
the palette command, later installer updates keep it removed. Uninstalling fman
removes its PATH entry.

Portable copies can also add their folder to PATH. Switch the command off before
moving or deleting a portable folder, because its PATH entry points to that
location. The status message warns about this when the command is enabled in a
portable copy.

This command is available only on Windows. Linux packages already install
`/usr/bin/fman`.
