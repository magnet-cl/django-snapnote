import base64
import json
import logging
import urllib.error
import urllib.request
import uuid

from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _

from . import conf

logger = logging.getLogger("snapnote")


def email(ticket, absolute_url):
    recipients = list(conf.get("NOTIFY_EMAILS"))
    if not recipients:
        return
    body = "\n".join(
        part
        for part in (
            ticket.description,
            f"{_('Page')}: {ticket.page_url}",
            f"{_('Ticket')}: {absolute_url}" if absolute_url else "",
        )
        if part
    )
    send_mail(
        subject=f"[Snapnote] {ticket.title}",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=recipients,
    )


JIRA_REQUIRED = conf.JIRA_REQUIRED
SLACK_REQUIRED = conf.SLACK_REQUIRED


def _slack_escape(text):
    """Escapes the three characters Slack mrkdwn treats as control (&, <, >).

    This also defuses <!channel>, <!here> and <@U123> mentions in untrusted text.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def slack(ticket, absolute_url):
    """Posts a short summary of the ticket to a Slack incoming webhook (no images).

    The ticket text is untrusted user input; it is escaped for Slack mrkdwn.
    """
    lines = [f"*{_slack_escape(ticket.title[:200])}*"]
    if ticket.description:
        description = ticket.description
        if len(description) > 500:
            description = description[:500] + "..."
        lines.append(_slack_escape(description))
    page = ticket.safe_page_url
    if page:
        lines.append("Page: <" + _slack_escape(page).replace("|", "%7C") + ">")
    elif ticket.page_url:
        lines.append(f"Page: {_slack_escape(ticket.page_url)}")
    if ticket.reported_by_id:
        lines.append(f"Reported by: {_slack_escape(str(ticket.reported_by))}")
    if absolute_url:
        lines.append("<" + absolute_url.replace("|", "%7C") + f"|Snapnote ticket #{ticket.pk}>")
    request = urllib.request.Request(
        conf.get("SLACK_WEBHOOK_URL"),
        data=json.dumps({"text": "\n".join(lines)}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=conf.get("SLACK_TIMEOUT")):  # noqa: S310
            pass
    except Exception as exc:
        # The webhook URL is a secret: re-raise without it in the message or the traceback.
        raise RuntimeError(f"Slack notifier failed: {short_error(exc)}") from None


def _jira_request(path, data, content_type, extra_headers=None):
    token = f"{conf.get('JIRA_EMAIL')}:{conf.get('JIRA_API_TOKEN')}".encode()
    request = urllib.request.Request(
        f"{conf.get('JIRA_URL').rstrip('/')}{path}",
        data=data,
        method="POST",
        headers={
            "Authorization": "Basic " + base64.b64encode(token).decode(),
            "Content-Type": content_type,
            "Accept": "application/json",
            **(extra_headers or {}),
        },
    )
    with urllib.request.urlopen(request, timeout=conf.get("JIRA_TIMEOUT")) as response:  # noqa: S310
        return json.loads(response.read() or b"{}")


def short_error(exc):
    """One short line describing a failure, safe to show to staff (no credentials)."""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode(errors="replace")
        except Exception:
            body = ""
        text = f"HTTP {exc.code}: {body}"
    elif isinstance(exc, urllib.error.URLError):
        text = f"Connection error: {exc.reason}"
    else:
        text = f"{type(exc).__name__}: {exc}"
    secrets = (
        conf.get("JIRA_API_TOKEN"),
        conf.get("JIRA_EMAIL"),
        conf.get("JIRA_READ_API_TOKEN"),
        conf.get("JIRA_READ_EMAIL"),
        conf.get("SLACK_WEBHOOK_URL"),
    )
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return " ".join(text.split())[:300]


def _adf_paragraph(*parts):
    """A paragraph in Atlassian Document Format; parts are text or (text, url) links."""
    content = []
    for part in parts:
        if isinstance(part, tuple):
            text, url = part
            content.append(
                {"type": "text", "text": text, "marks": [{"type": "link", "attrs": {"href": url}}]}
            )
        else:
            content.append({"type": "text", "text": part})
    return {"type": "paragraph", "content": content}


def _multipart(field, filename, content):
    boundary = uuid.uuid4().hex
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, f"multipart/form-data; boundary={boundary}"


def jira_issue(ticket, absolute_url):
    """Creates a Jira Cloud issue for the ticket and attaches its images.

    The ticket text is untrusted user input; it is only ever sent as plain text.
    """
    blocks = []
    if ticket.description:
        blocks.append(_adf_paragraph(ticket.description))
    page = ticket.safe_page_url
    blocks.append(
        _adf_paragraph("Page: ", (page, page))
        if page
        else _adf_paragraph(f"Page: {ticket.page_url}")
    )
    if absolute_url:
        blocks.append(_adf_paragraph("Snapnote ticket: ", (absolute_url, absolute_url)))
    if ticket.reported_by_id:
        blocks.append(_adf_paragraph(f"Reported by: {ticket.reported_by}"))
    payload = {
        "fields": {
            "project": {"key": conf.get("JIRA_PROJECT")},
            "issuetype": {"name": conf.get("JIRA_ISSUE_TYPE")},
            "summary": ticket.title[:255],
            "labels": list(conf.get("JIRA_LABELS")),
            "description": {"type": "doc", "version": 1, "content": blocks},
        }
    }
    try:
        issue = _jira_request("/rest/api/3/issue", json.dumps(payload).encode(), "application/json")
        key = issue["key"]
    except Exception as exc:
        ticket.jira_error = short_error(exc)
        ticket.save(update_fields=["jira_error"])
        raise
    # Saved right away: the attachments below are best effort and must not lose the key.
    ticket.jira_key = key
    ticket.jira_error = ""
    ticket.save(update_fields=["jira_key", "jira_error"])
    failures = []
    if conf.get("JIRA_ATTACH_IMAGES"):
        for name in ("screenshot", "annotations"):
            image = getattr(ticket, name)
            if not image:
                continue
            try:
                with image.open("rb") as handle:
                    body, content_type = _multipart(
                        "file", f"{name}-{ticket.pk}.png", handle.read()
                    )
                _jira_request(
                    f"/rest/api/3/issue/{key}/attachments",
                    body,
                    content_type,
                    {"X-Atlassian-Token": "no-check"},
                )
            except Exception as exc:
                # The issue exists already; a missing image must not fail the notifier.
                failures.append(f"{name}: {short_error(exc)}")
                logger.exception(
                    "Could not attach %s of ticket %s to Jira issue %s", name, ticket.pk, key
                )
    if failures:
        ticket.jira_error = ("Attachments failed - " + "; ".join(failures))[:300]
        ticket.save(update_fields=["jira_error"])
    return key


def run_notifiers(sender, ticket, request_url="", **kwargs):
    """Runs every configured notifier; a failing one never breaks the others."""
    from django.utils.module_loading import import_string

    for path in conf.get("NOTIFIERS"):
        try:
            notifier = import_string(path) if isinstance(path, str) else path
            notifier(ticket, request_url)
        except Exception:
            logger.exception("Snapnote notifier %r failed", path)
