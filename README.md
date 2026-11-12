# django-snapnote

Let your users report a problem from any page: a floating button captures the tab, lets them
draw on it and creates a ticket you can review in the admin or in built-in views.

Requires only Django (4.2–5.2) and Pillow. No DRF, no Node, no build step for you. The widget is a
self-contained bundle rendered in a Shadow DOM, so your CSS and ours don't interfere.

## Install

```bash
pip install django-snapnote
```

```python
# settings.py
INSTALLED_APPS += ["snapnote"]          # needs django.contrib.auth and staticfiles

# urls.py
path("snapnote/", include("snapnote.urls")),   # report endpoint + management views
```

```django
{# in your base template (the view needs the request context processor) #}
{% load snapnote_tags %}
{% snapnote_button %}
```

Then `python manage.py migrate`. Uploaded images use your `MEDIA_ROOT`/storage.

## Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `SNAPNOTE_CAN_REPORT` | `"snapnote.permissions.is_authenticated"` | Dotted path to `user -> bool`: who sees the button and may report |
| `SNAPNOTE_NOTIFIERS` | `["snapnote.notifiers.email"]` | Callables `(ticket, absolute_url)` run after a ticket is created |
| `SNAPNOTE_NOTIFY_EMAILS` | `[]` | Recipients of the email notifier (nothing is sent if empty) |
| `SNAPNOTE_BASE_TEMPLATE` | `None` | Template the management views extend; it only needs `{% block content %}` |
| `SNAPNOTE_ENABLE_MANAGEMENT_VIEWS` | `True` | List/detail views (the admin is always registered) |
| `SNAPNOTE_SEARCH_UNACCENT` | `False` | Accent-insensitive search (PostgreSQL + `django.contrib.postgres` only) |
| `SNAPNOTE_MAX_UPLOAD_MB` | `5` | Per-image size limit |
| `SNAPNOTE_MAX_DIMENSION` | `8000` | Max width/height in pixels |
| `SNAPNOTE_UPLOAD_TO` | `"snapnote/"` | Prefix in the storage |
| `SNAPNOTE_THROTTLE` | `"10/hour"` | Reports per user (`second`, `minute`, `hour`, `day`); uses Django's cache. `None` disables |
| `SNAPNOTE_AUTO_INJECT` | `False` | Also add `snapnote.middleware.AutoInjectMiddleware` to `MIDDLEWARE` to insert the button automatically. Incompatible with strict CSP and streaming responses |

Customise the look by overriding CSS variables on `#snapnote-root`
(`--snapnote-accent`, `--snapnote-accent-text`, `--snapnote-z-index`, `--snapnote-font`).

## Permissions

Reporting follows `SNAPNOTE_CAN_REPORT`. Managing uses the model permissions
`snapnote.view_ticket`, `change_ticket` and `delete_ticket` (superusers have them all).
Anonymous users are redirected to `LOGIN_URL`; authenticated users without permission get 403.

## Notifiers

The signal `snapnote.signals.ticket_created(sender, ticket, request_url)` is sent after commit.
A notifier is any callable; a failing one is logged and never breaks the report:

```python
# myproject/notifiers.py — Slack recipe
import requests
def slack(ticket, url):
    requests.post(settings.SLACK_WEBHOOK, json={"text": f"New ticket: {ticket.title} {url}"}, timeout=5)

SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.email", "myproject.notifiers.slack"]
```

### Jira notifier

Built in, opt-in and dependency-free (stdlib only). It creates a Jira Cloud issue per ticket, with the
page URL, a link to the Snapnote ticket and, optionally, the screenshot and annotations attached:

```python
SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.email", "snapnote.notifiers.jira_issue"]
SNAPNOTE_JIRA_URL = "https://yourcompany.atlassian.net"
SNAPNOTE_JIRA_EMAIL = "bot@yourcompany.com"
SNAPNOTE_JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]   # https://id.atlassian.com/manage-profile/security/api-tokens
SNAPNOTE_JIRA_PROJECT = "APP"                            # project key
# optional: SNAPNOTE_JIRA_ISSUE_TYPE = "Bug", SNAPNOTE_JIRA_LABELS = ["snapnote"],
#           SNAPNOTE_JIRA_ATTACH_IMAGES = True, SNAPNOTE_JIRA_TIMEOUT = 10
```

`manage.py check` warns (`snapnote.W002`) if a required setting is missing. Use a dedicated
Jira account with access only to that project. Notifiers run synchronously after commit with the
timeout above; for heavy use, wrap it in your own task queue. Screenshots may contain sensitive
data: they are attached to the issue, so keep `SNAPNOTE_JIRA_ATTACH_IMAGES = False` if the Jira
project is broader than who may see them.

## Export tickets for an AI coding assistant

```bash
python manage.py snapnote_export 42            # one or more IDs
python manage.py snapnote_export --open        # every open ticket
python manage.py snapnote_export 42 --output /tmp/tickets
```

Writes `snapnote-export/ticket-42/` with `ticket.md`, `ticket.json`, `screenshot.png`,
`annotations.png` and `screenshot_annotated.png` (the screenshot with the user's marks drawn on
it), so a tool like Claude Code can open the folder and see the problem without database access.
It reads from the database of the environment where it runs: to export production tickets, run it
there (or on a restored dump) and copy the folder.

The text of a ticket is written by an end user, so `ticket.md` labels it as untrusted data and
places it in code fences; still review any change an assistant proposes before merging it, and
do not export into a repository you will commit (screenshots can contain sensitive data).

## Security and deployment notes

- **Screenshots can contain sensitive data.** Serve `MEDIA_ROOT` only to authenticated staff (or use a
  private storage); do not expose it publicly. Purge old reports with
  `python manage.py snapnote_purge --older-than 90` (`--dry-run` to preview).
- **Permissions-Policy**: the browser needs `display-capture=(self)`. With `display-capture=()`
  (also sent by some proxies) capture never works and users get the upload fallback.
- **CSP**: allow `img-src blob: data:` and `style-src 'unsafe-inline'` (the Shadow DOM stylesheet
  is inline) and `script-src` for the static bundle.
- Uploads are validated (PNG/JPEG/WebP only, no SVG), size/dimension limited and re-encoded with Pillow.
- `page_url` must be http(s) and is never rendered as a clickable link otherwise.
- The report endpoint uses Django's CSRF protection; the template tag sets the cookie.
- Capture uses `getDisplayMedia` (desktop browsers). On mobile the user attaches an image.

## Development

```bash
pip install -e . pytest pytest-django
pytest                      # SQLite; SNAPNOTE_TEST_DB=postgres for PostgreSQL
cd frontend && npm ci && npm run build   # writes src/snapnote/static/snapnote/snapnote.js
npm test && npm run e2e
```

The built `snapnote.js` is committed/packaged so installing the wheel never needs Node.
