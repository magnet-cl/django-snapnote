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
- [x] Slack notifier (`snapnote.notifiers.slack`) via incoming webhook, stdlib only (`urllib`, no Slack SDK), with a
  system check for the missing `SNAPNOTE_SLACK_WEBHOOK_URL` setting. Ticket text is untrusted: escape it for Slack mrkdwn.
- [ ] Sync Jira status back into the ticket (read only, using `snapnote.jira`).
- [x] Crop the screenshot in the widget before sending, so the user can keep only the relevant area. The crop must be
  applied to the image itself (not just hidden), and it also helps with sensitive data (see the section below).
- [ ] Record server errors (HTTP 500) automatically as a ticket to resolve, with the exception, traceback summary, URL and
  user. Group repeated errors into one ticket (counter) instead of creating one per occurrence. Traceback and request
  data may hold sensitive values: scrub them and treat them as untrusted when rendering/exporting.
- [ ] Merge tickets: when two people report the same problem, merge one ticket into another, keeping the reporters,
  comments and images of both, with a link/trace of the merge (needs a new migration).
- [ ] Delayed capture for page state the flag can't preserve (hover menus, selects, anything that closes when the
  mouse leaves or the share dialog appears). After the user accepts the share dialog, hide the widget and count down
  (3-5 s, small chip excluded from the frame) so they can open what they want to show; then grab the frame. Make it
  configurable with `SNAPNOTE_CAPTURE_DELAY` (0 = capture immediately, as today; add to `conf.py` DEFAULTS, the
  template tag props and the README table). Complements the focus/click fix in Unreleased.
- [ ] Capture extra context in the widget (console errors, failed requests, viewport/browser info).
- [ ] More translations in `locale/` (only `es` exists besides English).
- [ ] Separate React and Angular components, installable from npm, for projects where Django is only the backend and
  the frontend is a web framework (SPA). Today the widget ships as a bundle injected by the Django template tag. The
  components should talk to the existing ticket endpoints (needs a documented, stable API, CSRF/session or token auth,
  and CORS guidance), reuse the capture/annotate/crop core instead of duplicating it, and keep the Shadow DOM isolation.

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
