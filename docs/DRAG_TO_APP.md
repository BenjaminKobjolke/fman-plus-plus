# Drag to last used app (Windows)

The "Drag to last used app" command sends the selected local files (or the file under the
cursor) into another app by drag and drop. It works like this:

1. fman shows up to five recently used app windows in a searchable list. The executable name
   appears beside each app, and the drag controls appear below the list. Press Enter to choose
   the highlighted app and start the drag, or Esc to cancel.
2. It brings the chosen window to the front and moves the mouse to the window's center.
3. It launches the bundled [windrop](https://github.com/BenjaminKobjolke/windrop) with
   `--keyboard`. The drag starts right away at the window's center: `WASD` or the arrow keys
   move the cursor (hold to keep moving), `Q`, `Space` or `Enter` drop the files, Esc cancels.
   Moving the real mouse and clicking drops too.

## Why windrop

fman used to fake the whole drag itself, calling `DoDragDrop` with no mouse button held and
moving the cursor programmatically. Many apps reject a drag like that. With windrop the user
starts the drag with the real mouse, which every drop target accepts.

## Bundling

`windrop.exe` is committed at `src/main/resources/base/Plugins/Core/bin/windows/`, next to
`7z.exe`. `fbs freeze` copies it like any other resource, so `python build.py freeze` alone
does not need Visual Studio.

`tools\build_windows.bat` runs `tools\update_windrop.bat` before it freezes, so a release build
always ships the current windrop. It needs Visual Studio and the windrop repo, and it may change
the committed exe. If the windrop build fails, fman is not built. To update windrop on its own,
run `tools\update_windrop.bat`:

- It runs `tools\build.bat` in the windrop repo. That script finds Visual Studio with `vswhere`
  and uses the CMake that ships with it.
- It then copies `build\Release\windrop.exe` into fman.
- The windrop repo is expected next to this one; set `WINDROP_DIR` to point elsewhere.

windrop links the C runtime statically, so no `vcruntime` DLL is needed.

To try a different build without re-vendoring, set `"windrop_path"` in `Core Settings.json`.
It takes precedence over the bundled exe, and must be a windrop that knows `--keyboard`.
