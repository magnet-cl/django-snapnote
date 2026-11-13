from django.core.management.base import BaseCommand, CommandError

from snapnote import conf
from snapnote.models import Ticket
from snapnote.notifiers import jira_issue


class Command(BaseCommand):
    help = "Retries creating the Jira issue of tickets whose creation failed (see the Jira column)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, dry_run, **options):
        if not conf.jira_enabled():
            raise CommandError(
                "The Jira notifier is not enabled or not fully configured "
                "(SNAPNOTE_NOTIFIERS and SNAPNOTE_JIRA_* settings)."
            )
        base = conf.get("BASE_URL").rstrip("/")
        done = failed = 0
        for ticket in Ticket.objects.jira("failed").order_by("pk"):
            if dry_run:
                self.stdout.write(f"Would retry ticket {ticket.pk}: {ticket.jira_error}")
                continue
            path = ticket.get_absolute_url() if conf.get("ENABLE_MANAGEMENT_VIEWS") else ""
            try:
                key = jira_issue(ticket, f"{base}{path}" if base and path else "")
            except Exception:
                failed += 1
                self.stderr.write(f"Ticket {ticket.pk} failed again: {ticket.jira_error}")
            else:
                done += 1
                self.stdout.write(f"Ticket {ticket.pk} -> {key}")
        if not dry_run:
            self.stdout.write(f"Created {done} issue(s), {failed} failed.")
