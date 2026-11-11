from urllib.parse import urlsplit

from django.conf import settings
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _

from . import conf


def screenshot_upload_to(instance, filename):
    return f"{conf.get('UPLOAD_TO')}screenshots/{filename}"


def annotations_upload_to(instance, filename):
    return f"{conf.get('UPLOAD_TO')}annotations/{filename}"


class TicketQuerySet(models.QuerySet):
    def search(self, term):
        term = (term or "").strip()
        if not term:
            return self
        from django.apps import apps
        from django.db import connection

        lookup = "icontains"
        if (
            conf.get("SEARCH_UNACCENT")
            and connection.vendor == "postgresql"
            and apps.is_installed("django.contrib.postgres")
        ):
            lookup = "unaccent__icontains"
        query = models.Q()
        for field in ("title", "description", "page_url"):
            query |= models.Q(**{f"{field}__{lookup}": term})
        return self.filter(query)


class Ticket(models.Model):
    """A problem reported by a user from any page, with an optional screenshot."""

    class Status(models.TextChoices):
        OPEN = "open", _("open")
        CLOSED = "closed", _("closed")

    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    # Not a URLField: it rejects intranet hosts and http://testserver/.
    page_url = models.CharField(_("page url"), max_length=2000)
    screenshot = models.ImageField(
        _("screenshot"), upload_to=screenshot_upload_to, blank=True, max_length=255
    )
    # Transparent layer with the annotations, kept apart from the screenshot.
    annotations = models.ImageField(
        _("annotations"), upload_to=annotations_upload_to, blank=True, max_length=255
    )
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.OPEN
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("reported by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snapnote_tickets",
    )
    closed_at = models.DateTimeField(_("closed at"), null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("closed by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = TicketQuerySet.as_manager()

    class Meta:
        verbose_name = _("ticket")
        verbose_name_plural = _("tickets")
        ordering = ("-created_at", "-pk")

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def get_absolute_url(self):
        try:
            return reverse("snapnote:ticket_detail", kwargs={"pk": self.pk})
        except NoReverseMatch:
            return ""

    @property
    def page_path(self):
        parts = urlsplit(self.page_url)
        path = parts.path or "/"
        return f"{path}?{parts.query}" if parts.query else path

    @property
    def safe_page_url(self):
        """page_url if its scheme is http(s), else empty (never render javascript: links)."""
        return self.page_url if urlsplit(self.page_url).scheme in ("http", "https") else ""

    def close(self, user):
        from django.utils import timezone

        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])

    def reopen(self):
        self.status = self.Status.OPEN
        self.closed_at = None
        self.closed_by = None
        self.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
