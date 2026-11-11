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
    return messages
