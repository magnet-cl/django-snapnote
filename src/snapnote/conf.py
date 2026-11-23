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
    # Optional read-only credentials for snapnote_jira_export; default to the JIRA_* ones above.
    "JIRA_READ_EMAIL": "",
    "JIRA_READ_API_TOKEN": "",
    # Slack notifier (snapnote.notifiers.slack): incoming webhook URL (required).
    "SLACK_WEBHOOK_URL": "",
    "SLACK_TIMEOUT": 10,
    # Public site URL (e.g. "https://intranet.example.com"), used to link tickets from Jira issues
    # created outside a request (snapnote_retry_jira).
    "BASE_URL": "",
}


def get(name):
    return getattr(settings, f"SNAPNOTE_{name}", DEFAULTS[name])


def get_callable(name):
    value = get(name)
    return import_string(value) if isinstance(value, str) else value


JIRA_NOTIFIER = "snapnote.notifiers.jira_issue"
SLACK_REQUIRED = ("SLACK_WEBHOOK_URL",)
JIRA_REQUIRED = ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT")


def jira_enabled():
    """True if the Jira notifier is active and fully configured."""
    return JIRA_NOTIFIER in get("NOTIFIERS") and all(get(name) for name in JIRA_REQUIRED)


def jira_read_credentials():
    """(email, token) used to read issues: the read-only pair if set, else the main one."""
    if get("JIRA_READ_API_TOKEN"):
        return get("JIRA_READ_EMAIL") or get("JIRA_EMAIL"), get("JIRA_READ_API_TOKEN")
    return get("JIRA_EMAIL"), get("JIRA_API_TOKEN")


def jira_read_configured():
    email, token = jira_read_credentials()
    return bool(get("JIRA_URL") and get("JIRA_PROJECT") and email and token)
