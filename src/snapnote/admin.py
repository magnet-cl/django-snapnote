from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Ticket


class JiraFilter(admin.SimpleListFilter):
    title = "Jira"
    parameter_name = "jira"

    def lookups(self, request, model_admin):
        return [("ok", _("In Jira")), ("failed", _("Jira failed")), ("none", _("No Jira"))]

    def queryset(self, request, queryset):
        return queryset.jira(self.value())


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "jira_key", "jira_error", "reported_by", "created_at")
    list_filter = ("status", JiraFilter, "created_at")
    search_fields = ("title", "description", "page_url", "jira_key")
    raw_id_fields = ("reported_by", "closed_by")
    readonly_fields = ("created_at", "updated_at")
