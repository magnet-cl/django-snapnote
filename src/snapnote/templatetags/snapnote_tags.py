from django import template
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext as _

from .. import conf

register = template.Library()


def get_labels():
    return {
        "report": _("Report a problem"),
        "title": _("Title"),
        "description": _("Description"),
        "preview": _("Preview"),
        "editAnnotations": _("Edit annotations"),
        "send": _("Send"),
        "cancel": _("Cancel"),
        "sending": _("Sending…"),
        "success": _("Thanks! Your report was sent."),
        "error": _("The report could not be sent. Try again."),
        "noCapture": _("Could not capture the screen. You can attach a screenshot instead."),
        "attach": _("Attach a screenshot"),
        "pen": _("Pen"),
        "rectangle": _("Rectangle"),
        "text": _("Text"),
        "undo": _("Undo"),
        "clear": _("Clear all"),
        "done": _("Done"),
        "titleRequired": _("The title is required."),
    }


def can_report(request):
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and conf.get_callable("CAN_REPORT")(user))


@register.inclusion_tag("snapnote/button.html", takes_context=True)
def snapnote_button(context):
    request = context.get("request")
    if request is None or not can_report(request):
        return {"show": False}
    # Also makes sure the CSRF cookie is set. The token travels in the props because the
    # cookie may be unreadable from JS (CSRF_COOKIE_HTTPONLY) or absent (CSRF_USE_SESSIONS).
    csrf_token = get_token(request)
    return {
        "show": True,
        "props": {
            "report_url": reverse("snapnote:report"),
            "csrf_token": csrf_token,
            "labels": get_labels(),
            "max_upload_mb": conf.get("MAX_UPLOAD_MB"),
        },
        "script_url": static("snapnote/snapnote.js"),
    }


def render_button(request):
    """Used by the auto-inject middleware."""
    from django.template.loader import render_to_string

    return render_to_string("snapnote/button.html", snapnote_button({"request": request}))


__all__ = ["snapnote_button"]
