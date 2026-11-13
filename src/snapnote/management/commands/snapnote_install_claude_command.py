from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

TEMPLATE = Path(__file__).resolve().parents[2] / "claude" / "ticket.md"
GITIGNORE_ENTRY = ".snapnote-tickets/"


class Command(BaseCommand):
    help = (
        "Installs the /ticket command for Claude Code into the project's .claude/commands/ "
        "directory. It is a copy: edit it to fit your project."
    )

    def add_arguments(self, parser):
        parser.add_argument("--target", help="project root (default: settings.BASE_DIR or cwd)")
        parser.add_argument("--force", action="store_true", help="overwrite local changes")

    def handle(self, *args, target, force, **options):
        root = Path(target or getattr(settings, "BASE_DIR", None) or Path.cwd())
        if not root.is_dir():
            raise CommandError(f"{root} is not a directory.")
        destination = root / ".claude" / "commands" / "ticket.md"
        content = TEMPLATE.read_text()

        if destination.exists():
            if destination.read_text() == content:
                self.stdout.write(f"{destination} is already up to date.")
            elif not force:
                raise CommandError(
                    f"{destination} exists and differs from the packaged template "
                    "(you probably customized it). Use --force to overwrite it."
                )
            else:
                destination.write_text(content)
                self.stdout.write(f"Overwrote {destination}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)
            self.stdout.write(f"Installed {destination}")

        self.ignore_exports(root)
        self.stdout.write(
            "Edit the 'Project settings' section, then use /ticket <id> in Claude Code."
        )

    def ignore_exports(self, root):
        """Keeps exported tickets (screenshots can be sensitive) out of git."""
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            self.stdout.write(f"Remember to add {GITIGNORE_ENTRY} to your .gitignore.")
            return
        lines = gitignore.read_text().splitlines()
        if GITIGNORE_ENTRY not in lines and GITIGNORE_ENTRY.rstrip("/") not in lines:
            suffix = "" if not lines or gitignore.read_text().endswith("\n") else "\n"
            with gitignore.open("a") as handle:
                handle.write(f"{suffix}{GITIGNORE_ENTRY}\n")
            self.stdout.write(f"Added {GITIGNORE_ENTRY} to {gitignore}")
