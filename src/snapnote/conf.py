from django.conf import settings
from django.utils.module_loading import import_string

DEFAULTS = {
    "CAN_REPORT": "snapnote.permissions.is_authenticated",
    "NOTIFIERS": ["snapnote.notifiers.email"],
    "NOTIFY_EMAILS": [],
    "BASE_TEMPLATE": None,
    "ENABLE_MANAGEMENT_VIEWS": True,
    "SEARCH_UNACCENT": False,
    "MAX_UPLOAD_MB": 5,
    "MAX_DIMENSION": 8000,
    "UPLOAD_TO": "snapnote/",
    "THROTTLE": "10/hour",
    "AUTO_INJECT": False,
    # Jira notifier (snapnote.notifiers.jira_issue). URL, EMAIL, API_TOKEN and PROJECT are required.
    "JIRA_URL": "",
    "JIRA_EMAIL": "",
    "JIRA_API_TOKEN": "",
    "JIRA_PROJECT": "",
    "JIRA_ISSUE_TYPE": "Bug",
    "JIRA_LABELS": ["snapnote"],
    "JIRA_ATTACH_IMAGES": True,
    "JIRA_TIMEOUT": 10,
}


def get(name):
    return getattr(settings, f"SNAPNOTE_{name}", DEFAULTS[name])


def get_callable(name):
    value = get(name)
    return import_string(value) if isinstance(value, str) else value
