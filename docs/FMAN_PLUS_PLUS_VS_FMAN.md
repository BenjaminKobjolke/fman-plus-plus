# fman++ vs. fman

fman++ is a fork of [mherrmann/fman](https://github.com/mherrmann/fman). This page summarizes features the fork adds or changes; it does not repeat features that work the same way in upstream fman. Follow each link for details.

## Licensing and privacy

- **No purchase or activation flow.** fman++ has no license key, trial, registration, feature gate or nag screen, and it no longer sends licensing telemetry. See [PURCHASING.md](PURCHASING.md).
- **Private navigation history.** Go To history can be kept only for the current session, and saved paths strip credentials. See [Go To](functions/go-to.md) (upstream [#185](https://github.com/mherrmann/fman/issues/185)).

## Navigation and panes

- **Remember the last selection.** Returning to a folder restores the last child you selected there. See [Remember last visited](functions/remember-last-visited.md) (upstream [#185](https://github.com/mherrmann/fman/issues/185)).
- **Select files with the right mouse button.** Turn on right-button selection to mark files with clicks or a drag, and hold for one second to open their context menu. See [Right-button selection](RIGHT_BUTTON_SELECTION.md) (upstream [#389](https://github.com/mherrmann/fman/issues/389)).
- **More capable Go To.** Fuzzy path completion handles environment variables, forward slashes and `..` segments on Windows. See [Go To](functions/go-to.md) (upstream [#175](https://github.com/mherrmann/fman/issues/175), [#118](https://github.com/mherrmann/fman/issues/118), [#98](https://github.com/mherrmann/fman/issues/98)).
- **Refresh changing folders.** Local, network and FTP folders can refresh while fman is open. See [Folder refresh](functions/FOLDER_REFRESH.md) (upstream [#170](https://github.com/mherrmann/fman/issues/170)).
- **Choose how many panes to use.** Start with one pane or add and remove panes as needed. See [Show only the active pane](functions/show-only-active-pane.md) and [Add and remove panes](functions/add-remove-panes.md) (upstream [#156](https://github.com/mherrmann/fman/issues/156), [#57](https://github.com/mherrmann/fman/issues/57)).
- **Follow Windows shortcuts.** Navigate to a `.lnk` file's destination instead of launching it. See [Follow shortcut](functions/follow-shortcut.md).
- **See drive capacity.** The Windows drive list can show total and free space. See [Drive space](functions/DRIVE_SPACE.md) (upstream [#49](https://github.com/mherrmann/fman/issues/49)).
- **Keep large folders responsive.** Directory loading and file-list updates avoid blocking the window. See [Large directories](LARGE_DIRECTORIES.md).
- **Keep your place when leaving private mode.** Pane locations are restored after incognito navigation ends. See [Go To](functions/go-to.md).

## Copy, move and delete

- **Run transfers in parallel.** Copy and move can transfer files while gathering the directory listing, with adjustable workers. See [Copy and Move](COPY_AND_MOVE.md).
- **Undo common file operations.** Restore changes from trash or reverse moves, renames and copies while they remain undoable. See [Undo](functions/undo.md) (upstream [#50](https://github.com/mherrmann/fman/issues/50)).
- **Recover from interrupted moves.** Completed local files are rolled back when a move stops early where it is safe to do so. See [Copy and Move](COPY_AND_MOVE.md) (upstream [#75](https://github.com/mherrmann/fman/issues/75)).
- **Handle file conflicts in more ways.** Compare file details, rename one conflict or automatically rename later conflicts. See [Copy and Move](COPY_AND_MOVE.md).
- **Control what happens after copying.** Successfully copied items can be deselected automatically. See [Copy and Move](COPY_AND_MOVE.md) (upstream [#112](https://github.com/mherrmann/fman/issues/112)).
- **Work with protected Windows folders.** File operations can request standard UAC elevation while the rest of fman stays unelevated. See [Elevation](functions/elevation.md).
- **Stop deletion safely.** Canceling a Windows recycle operation stops it when possible, and unsupported trash locations refuse instead of silently deleting permanently. See [Copy and Move](COPY_AND_MOVE.md) and [RoyI sync ledger](ROYI_SYNC.md).
- **Copy a file name or path directly.** Dedicated commands copy the selected item's name or full path. See [Key bindings](KEYBINDINGS.md) and [RoyI sync ledger](ROYI_SYNC.md).

## Viewers

- **Preview text, images and video in a pane.** Open files without leaving the file list, with a command palette and keys for each viewer. See [File viewers](viewers/FILE_VIEWERS.md).
- **Edit text and follow logs.** The text viewer can edit and save, search, format JSON and XML, reload changing files, and follow a log in tail mode. See [Text viewer](views/TEXT_VIEWER.md).
- **Browse images and video in place.** Images support zoom and camera rotation; video supports playback, seeking and volume. See [Image viewer](views/IMAGE_VIEWER.md) and [Video viewer](views/VIDEO_VIEWER.md).
- **Move between files without returning to the list.** Step through viewable files or preview one in the opposite pane. See [File viewers](viewers/FILE_VIEWERS.md).
- **Use file commands while viewing.** Rename, copy, move and delete the file from its viewer, with feedback in the status bar. See [File viewers](viewers/FILE_VIEWERS.md).
- **Open or view with one command.** Directories open normally while files open in the internal viewer. See [Open or View](functions/open-or-view.md).

## Archives

- **Browse more archives as folders.** `.rar` is available read-only, and `.xz` files can be opened through the bundled archive support. See [Archives](ARCHIVES.md) (upstream [#79](https://github.com/mherrmann/fman/issues/79), [#87](https://github.com/mherrmann/fman/issues/87)).
- **Work with archives faster on Windows.** ZIP, 7z and TAR operations have a moving progress display and are substantially faster. See [Archives](ARCHIVES.md).
- **Extend archive support through plugins.** Plugins can add archive formats and settings without replacing built-in ZIP, 7z and TAR handling. See [Plugins API](PLUGINS_API.md).

## Command palette and key bindings

- **Find commands more flexibly.** Search words can appear in any order, and alternative keywords can be added. See [Command palette](COMMAND_PALLETTE.md) and [Command palette keywords](COMMAND_PALETTE_KEYWORDS.md).
- **Rename palette entries.** Give a command the name you use while keeping its original name searchable. See [Command palette](COMMAND_PALLETTE.md).
- **Change shortcuts in the palette.** Rebind or remove a command's shortcut from its entry menu. See [Command palette key bindings](COMMAND_PALETTE_KEYBINDINGS.md).
- **Resize the palette and keep its width.** Long command names remain accessible in the resized window. See [Command palette](COMMAND_PALLETTE.md) (upstream [#163](https://github.com/mherrmann/fman/issues/163)).
- **Use pane-specific commands and status messages.** Commands and feedback can target the active pane, including panes added by plugins. See [Plugins API](PLUGINS_API.md) and [Status bar](STATUSBAR.md) (upstream [#59](https://github.com/mherrmann/fman/issues/59)).
- **Use familiar selection shortcuts.** Total Commander-style keypad commands select files by mask or extension. See [Key bindings](KEYBINDINGS.md) (upstream [#78](https://github.com/mherrmann/fman/issues/78)).

## Columns and file list

- **Show more file details.** Toggle Extension, Version and Attributes columns, including POSIX permissions where supported. See [Toggle columns](functions/TOGGLE_COLUMNS.md) (upstream [#184](https://github.com/mherrmann/fman/issues/184), [#67](https://github.com/mherrmann/fman/issues/67), [#48](https://github.com/mherrmann/fman/issues/48)).
- **Use the available list width.** The name column fills spare space instead of leaving unused room. See [Toggle columns](functions/TOGGLE_COLUMNS.md).
- **Switch a pane to compact multi-column view.** Show filenames in columns and keep each pane's view mode across restarts. See [Compact view](views/COMPACT_VIEW.md) (upstream [#214](https://github.com/mherrmann/fman/issues/214)).
- **Spot hidden files more easily.** Hidden entries have a distinct appearance, and Windows system-attribute entries follow the hidden-file filter. See [Hidden files](functions/hidden-files.md).
- **Keep the cursor in view.** An optional scroll margin keeps rows around the current selection visible. See [Scroll margin](SCROLL_MARGIN.md) (upstream [#186](https://github.com/mherrmann/fman/issues/186)).
- **Read and control status by pane.** Each pane can show its own status message, while the window status bar can be hidden. See [Status bar](STATUSBAR.md).

## Themes, fonts, icons and window

- **Choose a bundled theme or make your own.** Switch themes live or override colors and styling. See [Themes](THEMES.md) (upstream [#45](https://github.com/mherrmann/fman/issues/45), [#108](https://github.com/mherrmann/fman/issues/108)).
- **Pick a font for the whole interface.** Choose from bundled families and adjust pane and palette text size. See [Fonts](FONTS.md) and [Pane font size](functions/pane-font-size.md).
- **Choose an icon set and size.** Use bundled or custom file icons, including icons for common programming languages and folders. See [Icons](ICONS.md).
- **Add background images and transparency.** Themes can show a fitted image, and the window can be made translucent. See [Themes](THEMES.md) and [Window opacity](functions/window-opacity.md).
- **Customize the window chrome.** Hide the title bar or status bar, and control window title details. See [Window functions](WINDOW_FUNCTIONS.md) and [Window title and bars](WINDOW_TITLE_AND_BARS.md).
- **Minimize progress windows to the status bar.** Keep long-running tasks out of the way and restore them when needed. See [Status bar](STATUSBAR.md).

## Windows integration

- **Reuse one running window.** Opening a folder from Explorer or the command line sends it to the existing fman window. See [Single instance](SINGLE_INSTANCE.md) (upstream [#125](https://github.com/mherrmann/fman/issues/125)).
- **Minimize fman to the system tray.** Restore it with tray commands, a global shortcut or sign-in startup. See [System tray](SYSTEM_TRAY.md) (upstream [#144](https://github.com/mherrmann/fman/issues/144)).
- **Browse and connect network shares.** Go To accepts UNC and SMB paths, and the command palette can connect or disconnect shares. See [Windows network support](WINDOWS_NETWORK_SUPPORT.md) (upstream [#86](https://github.com/mherrmann/fman/issues/86)).
- **Use Robocopy for Windows transfers.** Copy and move through a destination picker with progress, retries, threading and optional logs. See [Robocopy](ROBOCOPY.md).
- **Keep network folders responsive.** Loading remote listings no longer freezes the window while Windows resolves icons and attributes. See [Windows network support](WINDOWS_NETWORK_SUPPORT.md).
- **Send files to another app by dragging.** Pick a recent target app and steer the drag with the keyboard. See [Drag to app](DRAG_TO_APP.md).
- **Open network locations in Explorer.** Launch the native file manager at a network share or computer. See [Windows network support](WINDOWS_NETWORK_SUPPORT.md).
- **Set file type actions.** Choose a persistent app or command for a file type, with the system default as fallback. See [File type actions](FILE_TYPE_ACTIONS.md) (upstream [#146](https://github.com/mherrmann/fman/issues/146)).

## Plugins and scripting

- **Find and install plugins in the app.** Search GitHub, see a plugin description, then install or reload without restarting. See [Installing plugins](INSTALL_PLUGINS.md) and [Plugins](PLUGINS.md).
- **Extend more parts of fman.** Plugins can add commands, columns, context menu entries, panes, file systems, archive formats and viewer behavior. See [Plugins API](PLUGINS_API.md).
- **React when a pane becomes active.** Plugins can register an activation callback and show pane-specific messages. See [Plugins API](PLUGINS_API.md) (upstream [#68](https://github.com/mherrmann/fman/issues/68)).
- **Debug plugins in an embedded console.** Inspect plugin output from inside fman. See [Console](CONSOLE.md).
- **Control fman from local scripts.** The authenticated scripting API exposes pane state and an allowlist of commands. See [Scripting API](SCRIPTING_API.md) (upstream [#76](https://github.com/mherrmann/fman/issues/76)).
- **Browse and operate on processes.** The optional ProcessFS plugin provides process browsing, and the built-in locking-process command finds which app is using selected files. See [Plugins](PLUGINS.md) and [Command palette](COMMAND_PALLETTE.md).

## Updates and release notes

- **Check for updates automatically or on demand.** Windows can check on a schedule, and the command palette can check manually. See [Check for updates](functions/check-for-updates.md).
- **Update from inside the app.** Download and install a newer release with a cancelable countdown, or open the release page. See [Check for updates](functions/check-for-updates.md).
- **Read past releases in fman.** Browse bundled release notes in the app, translated for many languages. See [Release notes](views/RELEASE_NOTES.md).

## Platform and build

- **Use a portable Windows build.** Keep settings and plugins beside the app and update the portable copy in place. See [Portable version](PORTABLE.md) (upstream [#82](https://github.com/mherrmann/fman/issues/82)).
- **Download a macOS disk image.** The project builds and publishes a `.dmg` release. See [macOS release process](CREATE_NEW_RELEASE_MAC.md).

## Where this list comes from

This summary is based on the feature notes in `release_notes/`, the upstream issue ledger in [UPSTREAM_ISSUES.md](UPSTREAM_ISSUES.md), and the Royi porting ledger in [ROYI_SYNC.md](ROYI_SYNC.md). When a new user-facing feature is added, add a line here and link its documentation.
