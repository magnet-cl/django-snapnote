from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SnapnoteConfig(AppConfig):
    name = "snapnote"
    verbose_name = _("Snapnote")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import checks, notifiers  # noqa: F401
        from .signals import ticket_created

        ticket_created.connect(notifiers.run_notifiers, dispatch_uid="snapnote.run_notifiers")
