# Install plugin

*Install plugin* is the command palette entry that finds fman plugins on
GitHub, downloads one, unpacks it into your data directory and loads it —
without a restart. This page documents how it does that, including exactly
which GitHub endpoints it talks to.

For where plugins live, load order and the other plugin commands, see
[`docs/PLUGINS.md`](PLUGINS.md). For writing one, see
[`docs/PLUGINS_API.md`](PLUGINS_API.md).

Implementation: `core/commands/plugins.py` (`InstallPlugin`),
`core/github.py`, `core/net.py`.

## Running it

- **Palette:** `Ctrl+Shift+P` → *Install plugin*. No default key binding.
  The name is derived from the class name `InstallPlugin` — the command has no
  `aliases`.
- **Command id:** `install_plugin`, an `ApplicationCommand`, so it is
  available regardless of which pane has focus.
- **With an argument:** `install_plugin` takes an optional `github_repo`
  parameter of the form `owner/name`. Passing it skips the picker and installs
  that repo directly. fman itself uses this — the "you pressed a key that does
  nothing" dialog offers `mherrmann/ArrowNavigation` and
  `mherrmann/SwitchPanesWithArrowKeys` that way
  (`fman/impl/nonexistent_shortcut_handler.py`).

## What happens, step by step

1. **Discover** — with no argument, fman queries GitHub's repository search
   for repos carrying *both* topics `fman` and `plugin`, excluding archived
   repos, and caches the result for the lifetime of the command object (one
   fetch per fman run). Archived repos are read-only, so installing one would
   pin a plugin that can never receive an update.
2. **Pick** — the results are shown in a quicksearch picker: plugin name,
   the repo description as the subtitle, and the star count as the hint
   (`123 ★`). Already-installed plugins are filtered out, matched by
   directory name in `Plugins\Third-party\`. See
   [Ordering](#ordering) for the sort.

3. **Review** — after a selection, fman loads `description.md` from the
   repository's default branch at `raw.githubusercontent.com` and renders it
   with Markdown formatting. If the file is missing, the request fails or the
   user is offline, the screen shows the plugin name, its short GitHub summary
   when available and *No description available.* Back (or Escape) returns to
   the picker with the search text kept; Install continues the normal install.
   This screen is only part of the picker flow. Passing `github_repo` directly
   still installs without it.
4. **Resolve a ref** — fman asks for the repo's *latest release* tag. If the
   repo has never published a release (HTTP 404), it falls back to the SHA of
   the newest commit on the default branch. So an unreleased plugin still
   installs; it is just pinned to a commit.

5. **Download** — the zipball for that ref.
6. **Unpack** — into `%APPDATA%\fman\Plugins\Third-party\<repo name>`.
7. **Record** — the repo's API URL and the installed ref are written into the
   plugin's `Plugin.json`.

8. **Load** — the plugin is loaded in place, at its correct position in the
   load order, and you get a *Plugin 'X' was successfully installed.* alert.

Steps 1, 3 and 5–6 show a status message (*Fetching available plugins…*,
*Downloading X…*) while they block.

## The GitHub endpoints

All of it is the public GitHub REST API over HTTPS, in `core/github.py`.
No API token, no `Authorization` header, no OAuth — every request is
anonymous.

| Step | Endpoint |
|------|----------|
| Search | `GET https://api.github.com/search/repositories?q=topic:fman+topic:plugin+archived:false` |
| Fetch one repo (`github_repo` argument) | `GET https://api.github.com/repos/<owner>/<name>` |
| Plugin description | `GET https://raw.githubusercontent.com/<owner>/<name>/<default-branch>/description.md` |
| Latest release | `GET .../repos/<owner>/<name>/releases/latest` |
| Latest commit | `GET .../repos/<owner>/<name>/commits` (first entry's `sha`) |
| Zipball | `GET .../repos/<owner>/<name>/zipball/<ref>` |

The last three URLs are not hardcoded: fman takes the `releases_url`,
`commits_url` and `archive_url` **URL templates** out of the repo JSON and
fills them in (`GitHubRepo._url`). Required placeholders such as
`{archive_format}` must be supplied; optional ones such as `{/id}` and
`{/sha}` are dropped when no value is given. So fman follows whatever URLs the
API hands it instead of assuming a URL shape.

Search results are paginated with `per_page=100`, looping `page=1,2,…` until
`page * 100 >= total_count`. GitHub's search API caps out at 1000 results, so
in practice this is a single page and the loop exists only for the day there
are more than 100 fman plugins.

The zipball URL redirects to `codeload.github.com`; the redirect is followed
transparently by the HTTP layer.

The description request uses `raw.githubusercontent.com`, not the GitHub REST
API, so it does not use the anonymous API request limit.

### Plugin authors

To show an explanation in fman's install screen, put a `description.md` file
in the repository root on its default branch. fman renders it as Markdown;
the file is optional.

### Ordering

The picker lists **most recently modified first, most-starred first among
equally recent ones**. `find_repos` sorts the results on the tuple
`(pushed_at, stargazers_count)`, descending, before handing them to the picker:

- `pushed_at` — the timestamp of the last commit pushed to any branch.
- Stars break ties only. A 900-star plugin last touched in 2019 still ranks
  below a one-star plugin pushed this morning; recency is the primary key and
  stars never override it.

The quicksearch dialog does no sorting of its own; it renders the order it is
given.

Two things this deliberately is not:

- **Not GitHub's own order.** The search URL carries no `sort=` parameter, so
  GitHub answers with its *best match* relevance ranking. For a query that is
  nothing but two topics, relevance is near-uniform and the resulting order is
  effectively arbitrary.
- **Not `sort=updated`.** GitHub's search API can sort, but only by the repo's
  `updated_at`, which any metadata change bumps — renaming the repo or editing
  its description would float an abandoned plugin to the top. `pushed_at` moves
  only when someone commits.

`pushed_at` is an ISO-8601 UTC string, so sorting it as text is already
chronological; no date parsing is involved. A repo that has never been pushed
to has no `pushed_at` and sorts to the bottom — where the star count then
decides the order among such repos.

Because `pushed_at` has second precision, ties are rare in practice: the star
tie-break mostly matters for plugins pushed by the same automation, or for the
never-pushed group. To rank by stars first instead, swap the two fields in the
`sorted` key in `find_repos`.

### Rate limits and privacy

- Anonymous GitHub API calls are limited to **60 requests/hour** per IP, and
  the **search** endpoint to **10 requests/minute**. A normal install is three
  or four requests. There is no way to configure a token, so on a shared or
  NAT'd IP a rate-limited response surfaces as an `HTTPError`.
- fman sends no identifying data with these requests — no token, no user id,
  nothing in the URL but the query. GitHub sees your IP and the default user
  agent.
- Nothing is contacted until you run the command. fman does not poll GitHub in
  the background, and there is no update check for installed plugins.

### How the request is made

`core/net.py::get_bytes` tries `urllib.request.urlopen` first. If that raises
`URLError` — in practice `SSL: CERTIFICATE_VERIFY_FAILED`, which some users
hit because the bundled Python's certificate store does not match the
system's — it retries the same URL with `requests`, which ships its own CA
bundle. A non-200 from the fallback is re-raised as an `HTTPError`, so callers
see one exception type either way. `HTTPError` is never swallowed by the
fallback: a 404 stays a 404, which is what the latest-release detection relies
on.

## Unpacking the zipball

The download is written to a temporary file and extracted through fman's own
`zip://` file system, **not** Python's `zipfile`. The reason is in a comment
in the source: `ZipFile` does not preserve the executable bit, which breaks
plugins that ship their own binaries. See [`docs/ARCHIVES.md`](ARCHIVES.md).

A GitHub zipball contains exactly one top-level directory
(`owner-repo-<sha>`); fman copies *that directory* to the destination, so the
SHA-suffixed wrapper does not end up in your plugins folder. If the
destination already exists the install aborts with *Plugin X seems to already
be installed.* — nothing is overwritten.

## Plugin.json

After a successful copy, fman merges two keys into the plugin's
`Plugin.json`, creating the file if the plugin does not ship one:

```json
{ "url": "https://api.github.com/repos/mherrmann/ArrowNavigation", "ref": "v1.0.2" }
```

`ref` is a release tag, or a 40-character commit SHA when the plugin had no
release. *List plugins* reads it back and shows it as the hint next to each
third-party plugin, abbreviating a SHA to its first 8 characters. `url` is
recorded for a future update feature — there is currently no *Update plugin*
command; updating means *Remove plugin*, then *Install plugin* again.

## Loading without a restart

The new plugin is inserted into the running load order rather than appended:
every plugin that sorts *after* it is unloaded, the new one is loaded, then
those are loaded again. Pane paths are saved and restored around the whole
operation (`PreservePanePaths`), because a pane sitting in a file system
provided by a reloaded plugin would otherwise lose its location.

If loading fails, no success alert is shown — but the files are already on
disk, so remove the directory (or use *Remove plugin*) before retrying.

## Failure modes

| Symptom | Cause |
|---------|-------|
| *Could not fetch available plugins: `<reason>`.* | Network, DNS or TLS failure during the search. Only the picker path catches this; passing `github_repo` explicitly lets the error propagate. |
| Nothing in the picker | No repo carries both the `fman` and `plugin` topics without being archived, or every one of them is already installed. |
| *Plugin X seems to already be installed.* | `Plugins\Third-party\<name>` exists. Remove it first. |
| HTTP 403 | GitHub rate limit — wait, or install by `github_repo` to spend fewer requests. |

## Installing without GitHub

Nothing about fman's plugin loader requires GitHub. Copy a plugin directory
into `%APPDATA%\fman\Plugins\User\` and run *Reload plugins*. On macOS and
Linux that path is `~/Library/Application Support/fman/Plugins/User` and
`~/.config/fman/Plugins/User`; setting `FMAN_DATA_DIRECTORY` moves it
anywhere.
