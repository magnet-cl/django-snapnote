# Changelog

## Unreleased

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
