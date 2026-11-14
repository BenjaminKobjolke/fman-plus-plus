"""
Central web links shown to the user (browser opens, alert <a href=...>).

Fork maintainers: this is the single place to retarget branded links at your own
site. Edit the values here at build time. This is intentionally NOT a runtime
setting in userdata — the URLs are baked into the build.

Named ``links`` (not ``urls``) to avoid confusion with ``fman.url``, which does
URL path manipulation, not web links.
"""
GITHUB_REPO      = 'BenjaminKobjolke/fman'
RELEASES         = 'https://github.com/%s/releases/latest' % GITHUB_REPO
HELP             = 'https://workflow-tools.com/fman-plus-plus/help/'
CHANGELOG        = RELEASES
ISSUES           = 'https://github.com/%s/issues' % GITHUB_REPO
ZEN              = HELP
TERMINAL_DOCS    = HELP
CUSTOM_SHORTCUTS = HELP
MACOS_DOCS       = HELP
FMAN_API         = 'https://fman.workflow-tools.com/'
