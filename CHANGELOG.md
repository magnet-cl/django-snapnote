# Changelog

## 0.8.0

- The report button no longer closes what the user wants to show in the screenshot: it doesn't take focus and its
  mouse/click events don't reach the host page's "click outside" handlers (e.g. open Bootstrap dropdowns stay open).
- Slack notifier `snapnote.notifiers.slack` (incoming webhook, stdlib only, no images, text escaped for mrkdwn).
  New settings `SNAPNOTE_SLACK_WEBHOOK_URL` and `SNAPNOTE_SLACK_TIMEOUT`; system check `snapnote.W003`.

## 0.7.0

- The widget lets users crop the screenshot (also an attached image) before annotating it. Only the chosen area
  is kept and sent; the full image is discarded in the browser. They can also skip the step.
- New labels (`crop`, `cropHint`, `applyCrop`, `resetCrop`, `skipCrop`) with Spanish translations.

## 0.6.0

- `snapnote_jira_export`: reads a Jira issue (read only, optional separate read credentials) into the same folder
  format as `snapnote_export`, so `/ticket APP-7` works without database or SSH access.
- The `/ticket` template accepts a Jira key. Re-run `snapnote_install_claude_command --force` to get it
  (your local edits to the file will be overwritten).

## 0.5.0

- Jira failures are visible: `Ticket.jira_error` (migration `0003`), a "Jira failed" badge in the list and detail,
  a Jira filter in the list and admin, a **Retry Jira** button and `manage.py snapnote_retry_jira`.
- New setting `SNAPNOTE_BASE_URL`.

## 0.4.0

- The Jira notifier stores the issue key in `Ticket.jira_key` (new migration `0002`). It is shown, with a link, in the
  list and detail views and the admin, is searchable, and is included in `snapnote_export`.

## 0.3.0

- `snapnote_install_claude_command`: installs a `/ticket` command for Claude Code (fetch the ticket, fix it, open a PR).

## 0.2.1

- Fix: the widget works with `CSRF_COOKIE_HTTPONLY = True` and `CSRF_USE_SESSIONS = True`. The CSRF token now
  travels in the page props; reading the cookie is only a fallback.
- `snapnote_export` command: exports tickets (markdown, JSON, images and an annotated composite) for people or AI assistants.

## 0.2.0

- Jira notifier (`snapnote.notifiers.jira_issue`) with image attachments and a system check.
- CI: Django 6.1 added to the matrix.

## 0.1.1

- First release on PyPI (0.1.0 was a TestPyPI dry run).

## 0.1.0

- First release: floating report button with tab capture (or image upload fallback), annotation
  editor, ticket model, report endpoint, management views, admin, notifiers, purge command.
