# File coloring

File coloring gives file names a color based on their extension. It is off by default. Run **Toggle file coloring** in the command palette to turn it on or off; the command applies the setting in both panes and reports the new state.

## Core settings

These options live in `Core Settings.json`:

| Setting | Default | Effect |
|---------|---------|--------|
| `file_coloring` | `false` | Enables the built-in file color rules. Use **Toggle file coloring** to change it while fman is running. |
| `file_color_rules` | See below | Ordered list of filename patterns and colors. The first matching rule wins. |

Example:

```json
{
  "file_coloring": true,
  "file_color_rules": [
    {"patterns": ["*.jpg", "*.png", "*.svg"], "color": "file_image_fg"},
    {"patterns": ["*.zip", "*.7z", "*.rar"], "color": "#fd971f"},
    {"patterns": ["*.exe", "*.bat", "*.ps1"], "color": "pane_new_fg"}
  ]
}
```

Patterns use case-insensitive filename matching and support shell-style wildcards such as `*.png`. A color can be a hex value or a theme color name; theme names follow the active theme. The default rules use the `file_image_fg`, `file_archive_fg`, `file_media_fg` and `file_program_fg` theme tokens, so their colors follow the active theme. The default rules cover common image, archive, audio/video and program extensions. Invalid settings use the defaults, and malformed rules are ignored.

The file color replaces the ordinary text color. Hidden files remain faded, and file-age shading remains layered over the color. Selected files and the row under the cursor keep their usual colors. See [File coloring in the plugin API](../PLUGINS_API.md#file-coloring) to color files from a plugin.
