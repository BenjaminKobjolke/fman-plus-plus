# External web links

All user-facing web links (help, changelog, buy, docs, etc.) live in one module:

    src/main/python/fman/links.py

Every link is a build-time constant. Fork maintainers retarget branded links by
editing that file — there is no runtime setting in userdata; the URLs are baked
into the build.

## Why one module

Links were previously hardcoded across seven files in two code regions
(`fman.impl` and the bundled Core plugin). Centralizing them means a fork
retargets its site in one place. Both regions import the module the same way:

```python
from fman import links
# ...
links.HELP
```

The module is named `links` (not `urls`) to avoid confusion with `fman.url`,
which does URL path manipulation, not web links.

## The links

| Constant           | Default                                | Used by                                |
|--------------------|----------------------------------------|----------------------------------------|
| `HELP`             | `https://workflow-tools.com/fman-plus-plus/help/` | Help command (F1)                      |
| `CHANGELOG`        | `https://github.com/BenjaminKobjolke/fman/releases/latest` | Startup "Updated to vX" status message |
| `ISSUES`           | `https://github.com/BenjaminKobjolke/fman/issues` | File-properties load-failure alert     |
| `ZEN`              | `https://workflow-tools.com/fman-plus-plus/help/` | "Zen of fman" command                  |
| `TERMINAL_DOCS`    | `https://workflow-tools.com/fman-plus-plus/help/` | Terminal / native-file-manager alerts  |
| `CUSTOM_SHORTCUTS` | `https://workflow-tools.com/fman-plus-plus/help/` | Key-bindings-updated alert             |
| `MACOS_DOCS`       | `https://workflow-tools.com/fman-plus-plus/help/` | First-run macOS setup tour             |
| `GITHUB_REPO`     | `BenjaminKobjolke/fman`                | GitHub update lookup                   |
| `RELEASES`        | `github.com/BenjaminKobjolke/fman/releases/latest` | Update download dialog |

## Retargeting a fork

Edit the constant in `src/main/python/fman/links.py`, then rebuild. Example:

```python
HELP = 'https://workflow-tools.com/fman-plus-plus/help/'
```

## Out of scope

`links.py` covers only user-facing web links. These are intentionally **not** in
it — they are build/infra config, not links a fork rebrands via the UI:

- Build/release config (`src/build/settings/*.json`, `release.json`)
- Error reporting: see [APP_ERROR_REPORTING.md](APP_ERROR_REPORTING.md). Metrics (`server_url`, `/metrics`) remain separate.
- Package/repo infra (`FBS_URL` in `tools/fbs_pro.py`, Dockerfiles)
- The QSettings organization domain `fman.io` (storage path, not a link)
