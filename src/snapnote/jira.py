"""Read-only access to Jira Cloud (stdlib only), used by snapnote_jira_export."""

import base64
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from . import conf

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
REDIRECTS = (301, 302, 303, 307, 308)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirects are followed by hand so credentials never travel to another host."""

    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _open(request):
    return _opener.open(request, timeout=conf.get("JIRA_TIMEOUT"))


def _auth_header():
    email, token = conf.jira_read_credentials()
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def get_json(path):
    request = urllib.request.Request(
        f"{conf.get('JIRA_URL').rstrip('/')}{path}",
        headers={"Authorization": _auth_header(), "Accept": "application/json"},
    )
    with _open(request) as response:
        return json.loads(response.read())


def download(url, max_bytes=None):
    """Downloads an attachment; returns None if it is larger than max_bytes."""
    max_bytes = max_bytes or MAX_ATTACHMENT_BYTES
    request = urllib.request.Request(url, headers={"Authorization": _auth_header()})
    try:
        response = _open(request)
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location") if exc.code in REDIRECTS else None
        if not location or urlsplit(location).scheme != "https":
            raise
        # Signed media URL on another host: no credentials.
        response = _open(urllib.request.Request(location))
    with response:
        data = response.read(max_bytes + 1)
    return None if len(data) > max_bytes else data


def adf_to_text(node):
    """Plain text from an Atlassian Document Format node."""
    kind = node.get("type")
    children = node.get("content", [])
    if kind == "text":
        text = node.get("text", "")
        for mark in node.get("marks", []):
            href = mark.get("attrs", {}).get("href")
            if mark.get("type") == "link" and href and href != text:
                return f"{text} ({href})"
        return text
    if kind == "hardBreak":
        return "\n"
    if kind in ("mention", "emoji"):
        return node.get("attrs", {}).get("text", "")
    if kind == "inlineCard":
        return node.get("attrs", {}).get("url", "")
    if kind in ("bulletList", "orderedList"):
        return "\n".join(f"- {adf_to_text(item)}" for item in children)
    if kind == "listItem":
        return "\n".join(adf_to_text(child) for child in children)
    if kind in ("doc", "blockquote"):
        return "\n\n".join(adf_to_text(child) for child in children)
    return "".join(adf_to_text(child) for child in children)
