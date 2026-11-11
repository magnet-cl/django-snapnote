from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from snapnote.models import Ticket


class Command(BaseCommand):
    help = "Deletes tickets (and their images) older than N days."

    def add_arguments(self, parser):
        parser.add_argument("--older-than", type=int, required=True, metavar="DAYS")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, older_than, dry_run, **options):
        cutoff = timezone.now() - timedelta(days=older_than)
        tickets = Ticket.objects.filter(created_at__lt=cutoff)
        count = tickets.count()
        if not dry_run:
            for ticket in tickets:
                ticket.screenshot.delete(save=False)
                ticket.annotations.delete(save=False)
                ticket.delete()
        verb = "Would delete" if dry_run else "Deleted"
        self.stdout.write(f"{verb} {count} ticket(s).")
