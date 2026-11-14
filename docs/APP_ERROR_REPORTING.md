# App error reporting

Released builds can send unexpected errors to fman-api so the fman++ maintainers can find and fix crashes. Automatic reporting starts only after consent. With automatic reporting off, the user can choose to send an individual report from its error dialog. Debug and development builds never send reports.

## What a report contains

Each report includes its kind (`unhandled`, `plugin` or `manual`), platform, fman version, exception type, message and stack trace. The operating system version and third-party plugin folder name are included when available.

Before delivery, fman redacts email addresses, bearer tokens, JWT-shaped values, recognized token formats and values following names such as `password`, `token`, `secret` and `key`. Messages are capped at 2,000 characters and stacks at 32,000 characters. The API validates, redacts and caps reports again. Reports do not include request headers, query strings, request bodies, or an IP address stored with the report.

## Delivery

Reports go to the fman-api `POST /api/v1/app-errors` route. Delivery runs on a background thread with a 10-second timeout. A report is deduplicated by its contents within one fman start, and at most 10 distinct reports are attempted per start. Offline reports and failed deliveries are dropped; failures are logged locally and are not sent as new reports.

The intake accepts `unhandled`, `plugin` and `manual` report kinds. An administrator can review reports through the protected, paged and filterable `GET /api/v1/app-errors` route.

## Consent and controls

The first-run start shows the tutorial, so it does not also ask about error reports. On a later start, if no choice has been saved, fman asks whether reports may be sent. Choosing Yes enables reporting; choosing No or closing the question disables it. The answer is saved in `%APPDATA%/fman/Local/Settings.json` under `error_reports`.

Run **Toggle error reports** from the command palette to change the setting while fman is open. When reporting is off, error dialogs include **Send report** to submit that individual report manually. The button does not enable automatic reporting.

The demo recording mode skips startup prompts. Metrics sent to `/metrics` are separate from app error reports.
