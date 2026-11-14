# Usage metrics

Frozen fman++ builds can send anonymous usage events to fman-api to help improve the app. Sending is off until the user chooses **Accept all** or **Only usage statistics** in the consent question. The separate `usage_metrics` setting is stored in the local settings file (`%APPDATA%/fman/Local/Settings.json` on Windows). The consent choice takes effect on the next start. Run **Toggle usage statistics** from the command palette to change the setting; restart fman for the change to take effect. Development builds never send usage metrics.

## What is sent

Each batch contains a random installation UUID, the platform, the fman version, and events with their UTC occurrence time and scalar properties. Events describe app starts, commands run, file interaction types (such as clicking a location bar, renaming or dropping a file), context menu use, tutorial progress, and shortcut handling. Properties can include command names, the shortcut pressed, the tutorial step, the way a context menu was opened, and text entered in the feedback field of the shortcut dialog.

Events have no dedicated fields for file or folder paths, file names, file contents, or account credentials. However, text entered in the shortcut dialog's feedback field is sent as an event property. Do not enter personal or sensitive information there.

The installation UUID is generated locally and saved in `Metrics.json`; fman does not create an account for metrics. The event batch has no dedicated name or email field.

## Batching and delivery

fman sends events in JSON batches when 20 events have accumulated, with no batch larger than 100 events. When fman closes, it queues the remaining events for delivery and waits up to three seconds for the metrics worker to flush them. Each request has a bounded timeout.

If a request fails, including when fman is offline, that batch is dropped. It is not retried or stored for later, and a metrics delivery failure does not prevent fman from closing or using the app.

## Reading metrics

Administrators can inspect received data through fman-api's protected routes:

- `GET /api/v1/metrics/counts` returns grouped event counts.
- `GET /api/v1/metrics/events` returns a paged list of raw events.

Both routes require administrator access. The events route supports paging and filters; the counts route groups events and reports totals. These routes are for administrators and are not available without authorization.

