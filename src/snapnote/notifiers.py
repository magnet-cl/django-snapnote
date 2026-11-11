import logging

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


def run_notifiers(sender, ticket, request_url="", **kwargs):
    """Runs every configured notifier; a failing one never breaks the others."""
    from django.utils.module_loading import import_string

    for path in conf.get("NOTIFIERS"):
        try:
            notifier = import_string(path) if isinstance(path, str) else path
            notifier(ticket, request_url)
        except Exception:
            logger.exception("Snapnote notifier %r failed", path)
