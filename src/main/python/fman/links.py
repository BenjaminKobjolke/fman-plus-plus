"""
Central web links shown to the user (browser opens, alert <a href=...>).

Fork maintainers: this is the single place to retarget branded links at your own
site. Edit the values here at build time. This is intentionally NOT a runtime
setting in userdata — the URLs are baked into the build.

Named ``links`` (not ``urls``) to avoid confusion with ``fman.url``, which does
URL path manipulation, not web links.
"""
HELP             = 'https://workflow-tools.com/fman-plus-plus/help'
CHANGELOG        = 'https://fman.io/changelog?s=f'
ISSUES           = 'https://fman.io/issues?s=f'
ZEN              = 'https://fman.io/zen'
TERMINAL_DOCS    = 'https://fman.io/docs/terminal?s=f'
CUSTOM_SHORTCUTS = 'https://fman.io/docs/custom-shortcuts?s=f'
MACOS_DOCS       = 'https://fman.io/docs/macos?s=f'
GITHUB_REPO      = 'BenjaminKobjolke/fman'
RELEASES         = 'https://github.com/%s/releases/latest' % GITHUB_REPO
FMAN_API         = 'https://fman.workflow-tools.com/'
