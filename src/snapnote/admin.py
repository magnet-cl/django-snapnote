from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "jira_key", "reported_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "page_url", "jira_key")
    raw_id_fields = ("reported_by", "closed_by")
    readonly_fields = ("created_at", "updated_at")
