# File-age shading

File-age shading changes how file rows look according to their modified date. It is off by default. Run **Toggle file age shading** in the command palette to turn it on or off; the command reports the new state briefly. The setting is applied in both panes and remains in effect when you change folders.

Only local `file://` URLs are shaded. Other file systems, missing timestamps, and timestamps that cannot be read are left unchanged. Future modified dates count as age zero. Selected rows and the cursor row keep their normal appearance so they remain easy to identify.

## Core settings

These options live in `Core Settings.json`:

| Setting | Default | Effect |
|---------|---------|--------|
| `file_age_shading` | `false` | Enables the built-in file-age shader. Use the **Toggle file age shading** command to change it while fman is running. |
| `file_age_scale` | `"log"` | `"log"` fades smoothly using `log1p(age_days) / log1p(file_age_full_days)`. `"steps"` uses four levels: under one day, under seven days, under thirty days, and thirty days or older. |
| `file_age_style` | `"transparency"` | `"transparency"` fades the row, `"tint"` blends its text with the `pane_new_fg` theme color, and `"bold"` makes files modified within the last day bold. |
| `file_age_full_days` | `365` | Positive number of days at which the logarithmic scale reaches its maximum. Values older than this are fully shaded. |

Invalid setting values fall back to their defaults. Transparency bottoms out at 40% opacity. In the stepped scale, the levels are 0 below one day, 1/3 below seven days, 2/3 below thirty days, and 1 from thirty days onward; `file_age_full_days` applies to the logarithmic scale.

The built-in shader uses the same modified date shown by the Modified column. For plugin-defined shading, see [File shading in the plugin API](../PLUGINS_API.md#file-shading).
