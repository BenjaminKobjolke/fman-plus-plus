# Thumbnail view

Thumbnail view shows files as a grid of image previews in a pane. Open the
command palette and run **Toggle thumbnail view** to switch the active pane.
Each pane remembers its view mode when fman closes. Selection, opening,
copying, moving, renaming, drag-and-drop and the context menu work as they do
in the other pane views.

Use **Increase font size** and **Decrease font size** (or Ctrl+mouse wheel) to
change the preview size while thumbnail view is active. The size is remembered
in Core Settings.json. These commands continue to change the font in other
views.

Core Settings.json supports these thumbnail settings:

| Setting | Default | Values |
| --- | --- | --- |
| `thumbnail_size` | `128` | Preview edge in pixels, from `48` to `512` |
| `thumbnail_previews` | `"images"` | `"images"` uses image previews; `"windows"` also asks Windows for previews of other local files, such as videos and PDFs |
| `thumbnail_locations` | `"local"` | `"local"` previews images in local folders only; `"everywhere"` also reads images in archives and remote locations |

Local-only previews are the default so opening a folder on an archive, FTP
server or phone does not unexpectedly download every image. Windows shell
previews always require a local path, even when `thumbnail_locations` is set to
`"everywhere"`. Shell previews are available on Windows only; other platforms
continue to use image previews.

Settings are read when fman starts and when thumbnail view is next enabled.
Changing Core Settings.json while fman is open does not reload the settings
into an already active thumbnail view.

See also [Compact view](COMPACT_VIEW.md).
