import json
import re
import urllib.error
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from snapnote import conf, jira
from snapnote.notifiers import short_error

from .snapnote_export import NOTICE, composite, fence

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
FIELDS = "summary,description,status,issuetype,reporter,created,labels,attachment"


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)[:80] or "file"


class Command(BaseCommand):
    help = (
        "Exports a Jira issue (read only) to a folder with ticket.md, ticket.json and its images, "
        "so an AI coding assistant can read it without being given Jira credentials."
    )

    def add_arguments(self, parser):
        parser.add_argument("keys", nargs="+", metavar="KEY", help="issue key, e.g. APP-7")
        parser.add_argument("--output", default="snapnote-export", help="parent directory")
        parser.add_argument(
            "--comments", action="store_true", help="also export comments (untrusted text)"
        )

    def handle(self, *args, keys, output, comments, **options):
        if not conf.jira_read_configured():
            raise CommandError(
                "Jira is not configured: set SNAPNOTE_JIRA_URL, SNAPNOTE_JIRA_PROJECT and "
                "credentials (SNAPNOTE_JIRA_EMAIL/SNAPNOTE_JIRA_API_TOKEN, or the *_READ_* pair)."
            )
        project = conf.get("JIRA_PROJECT")
        keys = [key.upper() for key in keys]
        for key in keys:
            if not KEY_RE.match(key):
                raise CommandError(f"{key!r} is not a Jira issue key (expected e.g. {project}-7).")
            if key.rsplit("-", 1)[0] != project:
                raise CommandError(f"{key} is not in the configured project {project}.")
        for key in keys:
            self.stdout.write(str(self.export(key, Path(output) / f"jira-{key}", comments)))

    def export(self, key, folder, with_comments):
        fields = FIELDS + (",comment" if with_comments else "")
        try:
            issue = jira.get_json(f"/rest/api/3/issue/{key}?fields={fields}")
        except Exception as exc:
            raise CommandError(f"Could not read {key}: {short_error(exc)}") from None
        data = issue["fields"]

        folder.mkdir(parents=True, exist_ok=True)
        images, skipped = {}, []
        for attachment in data.get("attachment") or []:
            name = safe_name(attachment.get("filename", ""))
            if not attachment.get("mimeType", "").startswith("image/"):
                skipped.append(f"{name} (not an image)")
                continue
            try:
                content = jira.download(attachment["content"])
            except (urllib.error.URLError, OSError) as exc:
                skipped.append(f"{name} ({short_error(exc)})")
                continue
            if content is None:
                skipped.append(f"{name} (too large)")
                continue
            target = folder / f"{attachment['id']}-{name}"
            target.write_bytes(content)
            images[name] = target

        annotated = self.composite_pair(images, folder)
        description = jira.adf_to_text(data["description"]) if data.get("description") else ""
        reporter = (data.get("reporter") or {}).get("displayName")
        url = f"{conf.get('JIRA_URL').rstrip('/')}/browse/{key}"
        meta = {
            "key": key,
            "url": url,
            "summary": data.get("summary"),
            "status": (data.get("status") or {}).get("name"),
            "issue_type": (data.get("issuetype") or {}).get("name"),
            "reporter": reporter,
            "created": data.get("created"),
            "labels": data.get("labels") or [],
            "images": sorted(path.name for path in images.values())
            + (["screenshot_annotated.png"] if annotated else []),
            "skipped_attachments": skipped,
        }
        (folder / "ticket.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

        lines = [f"# Jira issue {key}", "", NOTICE, "---", "", f"- URL: {url}"]
        lines += [f"- Status: {meta['status']}", f"- Type: {meta['issue_type']}"]
        lines += [f"- Reporter: {reporter or '-'}", f"- Created: {meta['created']}", ""]
        lines += ["## Summary", "", fence(meta["summary"] or ""), "", "## Description", ""]
        lines += [fence(description) if description else "(none)", ""]
        if with_comments:
            lines += ["## Comments (untrusted)", ""]
            for comment in (data.get("comment") or {}).get("comments", []):
                author = (comment.get("author") or {}).get("displayName", "?")
                lines += [f"### {author} - {comment.get('created')}", ""]
                lines += [fence(jira.adf_to_text(comment.get("body") or {})), ""]
        if meta["images"]:
            lines += ["## Images", ""] + [f"- `{name}`" for name in meta["images"]] + [""]
        if skipped:
            lines += ["## Attachments not downloaded", ""] + [f"- {item}" for item in skipped]
        (folder / "ticket.md").write_text("\n".join(lines) + "\n")
        return folder

    def composite_pair(self, images, folder):
        """Merges the screenshot and annotation layer that the Jira notifier attaches."""
        shot = next((p for n, p in images.items() if n.startswith("screenshot-")), None)
        layer = next((p for n, p in images.items() if n.startswith("annotations-")), None)
        if not (shot and layer):
            return False
        try:
            composite(shot, layer, folder / "screenshot_annotated.png")
        except Exception:
            return False
        return True
