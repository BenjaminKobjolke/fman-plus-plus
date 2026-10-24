# Upstream issues ledger

Which open issues of the original fman tracker have been looked at, and what was done.
Maintained by the `upstream-issues` skill (`.claude/skills/upstream-issues/SKILL.md`).

Source: https://github.com/mherrmann/fman/issues (read-only — never comment there)

An issue that is in this table has been handled. The next run takes the next five open
issues that are not in it, oldest first. Newest rows go at the top.

Status: `fixed`, `already fixed` (works here already), `skipped` (with reason),
`deferred` (fixable, but too big or needs a decision — with what is needed).

| Issue | Title | Labels | Status | Date | Note |
|-------|-------|--------|--------|------|------|
| [#38](https://github.com/mherrmann/fman/issues/38) | Visual feedback when copying/cutting files | enhancement, 16 votes | already fixed | 2026-10-24 | Copy and Cut show a three-second status message naming the files; the upstream comments confirm this shipped in fman 1.4.6. |
| [#35](https://github.com/mherrmann/fman/issues/35) | ".." entry in folders | enhancement, 35 votes | deferred | 2026-10-24 | A parent-directory row needs a product decision because fman deliberately uses keyboard navigation to save screen space; Backspace and Ctrl+Up already go up. |
| [#34](https://github.com/mherrmann/fman/issues/34) | Multiple tabs | enhancement, 108 votes | deferred | 2026-10-24 | Multiple tabs are a substantial UI/session change and conflict with fman's stated screen-space direction; needs a separately approved plan and product decision. |
| [#33](https://github.com/mherrmann/fman/issues/33) | WebDAV support | enhancement, 1 vote | deferred | 2026-10-24 | WebDAV needs a remote-protocol filesystem subsystem or dependency decision; needs a separately approved plan. |
| [#32](https://github.com/mherrmann/fman/issues/32) | SCP support | enhancement, 11 votes | skipped | 2026-10-24 | Duplicate of #31 (deferred): the upstream discussion says SCP is outdated and points to SFTP. |
| [#28](https://github.com/mherrmann/fman/issues/28) | fman becomes very slow after pressing Alt+F1 when there are disconnected network drives | bug, windows | fixed | 2026-10-24 | Drive labels no longer query volume information for mapped network drives; `drives.py` and `test_drives.py`. |
| [#31](https://github.com/mherrmann/fman/issues/31) | SFTP support | enhancement, 43 votes | deferred | 2026-10-24 | Adding SFTP requires a protocol subsystem or dependency decision; needs a separately approved plan. |
| [#30](https://github.com/mherrmann/fman/issues/30) | FTP support | enhancement, 8 votes | deferred | 2026-10-24 | Adding FTP requires a protocol subsystem or dependency decision; needs a separately approved plan. |
| [#29](https://github.com/mherrmann/fman/issues/29) | File search | enhancement, 47 votes | already fixed | 2026-10-24 | Covered by the JustSearch plugin (README Plugins list): dialog, names and text in files, wildcards and regex, results as a search:// pane listing. Remaining gaps (Alt+F7, results straight to pane, delete/move on results, several wildcards) in JustSearch todo #12728. |
| [#27](https://github.com/mherrmann/fman/issues/27) | Associate .png file with any app other than Preview (eg. Sublime Text). Then fman only displays a very generic "file icon" for files of that type | bug, mac, 1 vote | skipped | 2026-10-24 | macOS file-association icon behavior cannot be reproduced or tested on this Windows fork. |
| [#19](https://github.com/mherrmann/fman/issues/19) | Double-_right_clicking has same effect as normal double click | bug, 1 vote | skipped | 2026-10-23 | The issue has no description or reproduction steps; needs an actionable example to distinguish the intended behavior. |
| [#20](https://github.com/mherrmann/fman/issues/20) | fman displays app icon for file type associated with that app, even after the app was uninstalled | bug, mac, 1 vote | skipped | 2026-10-23 | macOS-only Finder icon-cache behavior; cannot be reproduced or tested on Windows. |
| [#23](https://github.com/mherrmann/fman/issues/23) | fman doesn't realise external drive was disconnected on startup | bug, windows | already fixed | 2026-10-23 | `SessionManager.open_path_in_pane` falls back to the closest existing parent or the home directory when the saved path is gone. |
| [#24](https://github.com/mherrmann/fman/issues/24) | Uninstalling via Control Panel requires administrator privileges, executing uninstall.exe doesn't | bug, windows | deferred | 2026-10-23 | The installer supports both per-user and all-user installs; deciding whether Control Panel should elevate or uninstall machine-wide installs differently needs a product decision. |
| [#26](https://github.com/mherrmann/fman/issues/26) | 360 Total Security claims fman is a trojan |  | skipped | 2026-10-23 | Antivirus false-positive support issue with no actionable code change or reproducible technical details. |
| [#17](https://github.com/mherrmann/fman/issues/17) | Icons are sometimes not displayed | bug, windows | deferred | 2026-10-23 | The report gives no reproducible steps or affected file types; needs a concrete Windows example before a fix can be pinned. |
| [#16](https://github.com/mherrmann/fman/issues/16) | Files and directories in SMB-Shares are not displayed | bug, windows | already fixed | 2026-10-23 | UNC paths use `LocalFileSystem.iterdir` and `os.listdir`; the Windows Network view enumerates servers and shares. |
| [#15](https://github.com/mherrmann/fman/issues/15) | Icon for .lnk files on Desktop are not shown | bug, windows | already fixed | 2026-10-23 | Windows shell icons are used by the System set; when another set is active, the executable-icon toggle restores real `.lnk` icons. |
| [#13](https://github.com/mherrmann/fman/issues/13) | .lnk to virtual network drive (Z:) is not displayed | bug, windows | deferred | 2026-10-23 | The issue has no description or reproduction details; needs a concrete shortcut and drive setup to verify. |
| [#12](https://github.com/mherrmann/fman/issues/12) | .lnk files are displayed as the name of the link target instead of the link itself | bug, windows, 1 vote | already fixed | 2026-10-23 | The Name column uses the filesystem name, which returns the final local path component without resolving the `.lnk` target. |
| [#1](https://github.com/mherrmann/fman/issues/1) | Icons have a low resolution | bug, mac, 5 votes | skipped | 2026-10-23 | macOS/Linux Finder `.icns` issue; Windows icons come from the shell or crisp vector icons. |
| [#3](https://github.com/mherrmann/fman/issues/3) | Trying to delete un-deletable file raises exception | bug, linux, 2 votes | already fixed | 2026-10-23 | Core deletion reports access errors and offers UAC elevation for protected files. |
| [#5](https://github.com/mherrmann/fman/issues/5) | Try deleting un-deletable file: fman freezes | bug, mac | skipped | 2026-10-23 | macOS-only report; deletion runs as a background task here. |
| [#8](https://github.com/mherrmann/fman/issues/8) | Can't resize fman to width < status bar | bug | fixed | 2026-10-23 | `widgets.py` MainWindow status bar label; `status_bar_test.py`. |
| [#9](https://github.com/mherrmann/fman/issues/9) | Can't enter "^" and "~" with a Swedish keyboard layout | bug, linux, 2 votes | skipped | 2026-10-23 | Linux-only keyboard-layout report; upstream comments confirm it works on Windows. |
