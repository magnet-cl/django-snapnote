# TODO

Things we want to do in django-snapnote. Mark with `[x]` when done and move the note to `CHANGELOG.md`.

## Verification (not tested yet)

- [ ] Real browser screen-share prompt (`getDisplayMedia`) in Chrome, not only the Playwright stub.
- [ ] Widget in Firefox, Safari and mobile browsers.
- [ ] PostgreSQL `unaccent` search (CI runs PostgreSQL, but the `unaccent` path is not covered locally).
- [ ] The `/ticket` command inside Claude Code, end to end (fetch ticket, fix, open PR).

## Features

- [ ] Ticket status workflow beyond the current states (assignee, comments, history).
- [ ] More notifiers (generic webhook, other trackers) behind the existing notifier interface, without adding dependencies.
- [ ] Slack notifier (`snapnote.notifiers.slack`) via incoming webhook, stdlib only (`urllib`, no Slack SDK), with a
  system check for the missing `SNAPNOTE_SLACK_WEBHOOK_URL` setting. Ticket text is untrusted: escape it for Slack mrkdwn.
- [ ] Sync Jira status back into the ticket (read only, using `snapnote.jira`).
- [x] Crop the screenshot in the widget before sending, so the user can keep only the relevant area. The crop must be
  applied to the image itself (not just hidden), and it also helps with sensitive data (see the section below).
- [ ] Capture extra context in the widget (console errors, failed requests, viewport/browser info).
- [ ] More translations in `locale/` (only `es` exists besides English).

## Sensitive and confidential information

Context: someone almost took a screenshot of a contract list that included salaries. The goal is that sensitive
data does not enter the system, and that if it does, it cannot travel further than intended.

- [ ] Mandatory preview with a redaction tool (blur / black out areas) before sending. The redaction must be burned
  irreversibly into the final image, not kept as a removable annotation layer (today screenshot and annotations are
  stored separately).
- [ ] Pages without screenshot: a setting or callable (`SNAPNOTE_SCREENSHOT_ALLOWED`) to disable the capture, or the
  whole button, on given views. The text report stays available.
- [ ] "Send without screenshot" option, visible in the form, so nobody feels forced to attach an image.
- [ ] Per-ticket "confidential" flag (set by the reporter or by rules). It restricts who can see the ticket and makes
  every notifier (email, Jira, Slack) and `snapnote_export` leave out its images and text. Needs a new migration.
- [ ] Image policy per notifier: no notifier sends images by default (Jira already has `JIRA_ATTACH_IMAGES`); document it
  in the README.
- [ ] Retention: `SNAPNOTE_RETENTION_DAYS` and a `snapnote_purge` command to delete old or closed images (or tickets).
  Also delete the physical files when a ticket is deleted.
- [ ] Images only behind authentication: check that they are not served from a public, guessable `MEDIA_URL`; serve them
  through a view with permission checks and document the setup.
- [ ] Access log: who viewed or exported a ticket or an image (new model and migration).

## Quality

- [ ] Keep the frontend bundle (`snapnote.js`) size in check; add a size budget to CI.
- [ ] Accessibility review of the widget (keyboard navigation, focus handling inside the Shadow DOM).
- [ ] Documentation: troubleshooting section in the README (CSRF settings, CSP, Jira credentials).

## Release / maintenance

- [ ] Review the supported Python/Django matrix when new versions are released.
- [ ] Automate the release checklist (version bump, changelog, tag) in a script.
