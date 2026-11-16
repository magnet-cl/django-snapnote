# django-snapnote

Reusable Django app (PyPI: `django-snapnote`, repo `magnet-cl/django-snapnote`, git remote `github`).
Users report a problem from any page with a floating button (tab capture + annotations); tickets are
reviewed in built-in views or the admin and can create Jira issues. Read `README.md` for the user-facing
features and settings; this file is what you need to work on the code.

## Hard rules

- Runtime dependencies: **Django and Pillow only**. No DRF, django-filter, Bootstrap, Postgres-only
  features, Slack, etc. Host projects are generic Django; assume nothing from them except
  `django.contrib.auth`, `staticfiles` and `AUTH_USER_MODEL` (never import `User`; users may have no `email`).
- Supported: Python >= 3.10, Django 4.2, 5.0, 5.1, 5.2, 6.1 (6.1 needs Python >= 3.12).
- Never edit a published migration; model changes get a new one (`0001`-`0003` exist).
- Ticket and Jira text written by users is **untrusted input**: render it escaped, write it to exports
  inside code fences with the "untrusted data" notice, never as instructions or `javascript:` links.
- Credentials must never appear in stored errors, logs or output (`notifiers.short_error` redacts them).
- Settings are read through `snapnote/conf.py` (`SNAPNOTE_*`, defaults in `DEFAULTS`). Add new ones there
  and in the README table.

## Layout

- `src/snapnote/`: `models`, `forms` (image validation/re-encoding), `views`, `urls`, `admin`,
  `notifiers` (email, Jira), `jira` (read-only client), `signals`, `checks`, `middleware` (opt-in),
  `templatetags/snapnote_tags.py` (the button), `management/commands/`, `templates/`, `locale/es/`,
  `claude/ticket.md` (template installed by `snapnote_install_claude_command`).
- `frontend/`: React + Vite widget rendered in a Shadow DOM. It builds into
  `src/snapnote/static/snapnote/snapnote.js`, which **is committed** and ships in the wheel.
- `tests/`: pytest-django with its own project in `tests/testproject/`.

## Commands

```bash
. .venv/bin/activate            # venv was made with virtualenv (python3-venv is not installed)
python -m pytest -q             # SQLite
SNAPNOTE_TEST_USER=custom python -m pytest -q   # custom user model without email
SNAPNOTE_TEST_DB=postgres python -m pytest -q   # needs PostgreSQL (CI runs it; not available locally)
ruff check . && ruff format src tests
python -m django makemigrations snapnote -n <name> --settings=tests.testproject.settings

cd frontend && npm ci
npm run typecheck && npm test && npm run build   # rebuild and commit snapnote.js when src/ changes
npm run e2e                     # real Chrome via Playwright, stubbed getDisplayMedia; needs ../.venv
```

- Translations: `msgfmt`/`makemessages` are not installed. Edit `locale/es/LC_MESSAGES/django.po` and
  regenerate the `.mo` with `polib` (`po.save_as_mofile(...)`). English is the source language.
- Tests that rely on `transaction.on_commit` use `django_capture_on_commit_callbacks(execute=True)`.
- Jira is always mocked in tests (`urllib.request.urlopen` / `snapnote.jira._open`).

## Releasing to PyPI

1. Bump `__version__` in `src/snapnote/__init__.py` and rename "Unreleased" in `CHANGELOG.md`.
   Model changes -> minor version; fixes -> patch.
2. Run tests and `ruff`, commit, push `main`, and wait for CI to be green (matrix Python x Django x
   SQLite/PostgreSQL, frontend job, bundle-is-up-to-date check). There is no `gh` CLI: read CI with
   `curl https://api.github.com/repos/magnet-cl/django-snapnote/actions/runs?head_sha=<sha>`.
3. Tag `vX.Y.Z` on that commit and push the tag. The `publish` job uses trusted publishing (OIDC),
   environment `pypi`, and may wait for manual approval in the Actions tab. No tokens in the repo.
4. Verify: `pip install django-snapnote==X.Y.Z` in a clean venv and run the tests against the
   installed wheel. PyPI's listing and JSON are cached for a few minutes; a 404 right after publishing
   is normal (query `/pypi/django-snapnote/X.Y.Z/json` with a random query string).
5. Versions cannot be reused once uploaded, so never retag a published version.

## Do not commit

`handout-paquete-pypi-tickets.md` (design notes mentioning internal systems), `.claude/settings.json`
(personal permissions), `dist/`, `.venv/`, `frontend/node_modules/`, exported tickets
(`.snapnote-tickets/`, `snapnote-export/`).

## Not verified yet

Real browser screen-share prompt, Firefox/Safari/mobile, PostgreSQL `unaccent` search, and the
`/ticket` command inside Claude Code have only been tested with stubs or not at all.
