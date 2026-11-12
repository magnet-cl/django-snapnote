from django.apps import apps
from django.core.checks import Warning, register
from django.db import connection

from . import conf


@register()
def check_settings(app_configs, **kwargs):
    messages = []
    if conf.get("SEARCH_UNACCENT") and (
        connection.vendor != "postgresql" or not apps.is_installed("django.contrib.postgres")
    ):
        messages.append(
            Warning(
                "SNAPNOTE_SEARCH_UNACCENT is ignored.",
                hint="It needs PostgreSQL and 'django.contrib.postgres' in INSTALLED_APPS "
                "(plus the unaccent extension).",
                id="snapnote.W001",
            )
        )
    notifiers = conf.get("NOTIFIERS")
    if "snapnote.notifiers.jira_issue" in notifiers:
        from .notifiers import JIRA_REQUIRED

        missing = [f"SNAPNOTE_{name}" for name in JIRA_REQUIRED if not conf.get(name)]
        if missing:
            messages.append(
                Warning(
                    "The Jira notifier is enabled but misconfigured.",
                    hint="Missing settings: " + ", ".join(missing),
                    id="snapnote.W002",
                )
            )
    return messages
