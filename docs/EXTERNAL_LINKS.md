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
| `HELP`             | `fman.io/docs/key-bindings?s=f`        | Help command (F1)                      |
| `CHANGELOG`        | `fman.io/changelog?s=f`                | Startup "Updated to vX" status message |
| `ISSUES`           | `fman.io/issues?s=f`                   | File-properties load-failure alert     |
| `ZEN`              | `fman.io/zen`                          | "Zen of fman" command                  |
| `TERMINAL_DOCS`    | `fman.io/docs/terminal?s=f`            | Terminal / native-file-manager alerts  |
| `CUSTOM_SHORTCUTS` | `fman.io/docs/custom-shortcuts?s=f`    | Key-bindings-updated alert             |
| `MACOS_DOCS`       | `fman.io/docs/macos?s=f`               | First-run macOS setup tour             |
| `GITHUB_REPO`     | `BenjaminKobjolke/fman`                | GitHub update lookup                   |
| `RELEASES`        | `github.com/BenjaminKobjolke/fman/releases/latest` | Update download dialog |

## Retargeting a fork

Edit the constant in `src/main/python/fman/links.py`, then rebuild. Example:

```python
HELP = 'https://workflow-tools.com/fast-file-manager/help'
```

## Out of scope

`links.py` covers only user-facing web links. These are intentionally **not** in
it — they are build/infra config, not links a fork rebrands via the UI:

- Build/release config (`src/build/settings/*.json`, `release.json`)
- Telemetry (`sentry_dsn`, `bin/post-commit`)
- Package/repo infra (`FBS_URL` in `tools/fbs_pro.py`, `src/repo/`, Dockerfiles)
- The QSettings organization domain `fman.io` (storage path, not a link)
