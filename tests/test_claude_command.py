import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from snapnote.management.commands.snapnote_install_claude_command import TEMPLATE


def install(root, **kwargs):
    call_command("snapnote_install_claude_command", target=str(root), **kwargs)


def test_template_has_the_essentials():
    text = TEMPLATE.read_text()
    assert text.startswith("---\n") and "argument-hint" in text
    assert "$ARGUMENTS" in text and "snapnote_export" in text
    assert "untrusted" in text.lower() and "Never push to or merge" in text


def test_installs_into_claude_commands(tmp_path):
    install(tmp_path)
    assert (tmp_path / ".claude" / "commands" / "ticket.md").read_text() == TEMPLATE.read_text()


def test_idempotent_and_protects_local_edits(tmp_path):
    install(tmp_path)
    install(tmp_path)  # same content: fine
    path = tmp_path / ".claude" / "commands" / "ticket.md"
    path.write_text("my own version")
    with pytest.raises(CommandError, match="--force"):
        install(tmp_path)
    assert path.read_text() == "my own version"
    install(tmp_path, force=True)
    assert path.read_text() == TEMPLATE.read_text()


def test_gitignore_gets_the_exports_entry_once(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules/")  # no trailing newline
    install(tmp_path)
    install(tmp_path)
    assert (tmp_path / ".gitignore").read_text() == "node_modules/\n.snapnote-tickets/\n"


def test_missing_gitignore_is_not_created(tmp_path):
    install(tmp_path)
    assert not (tmp_path / ".gitignore").exists()


def test_bad_target(tmp_path):
    with pytest.raises(CommandError):
        install(tmp_path / "nope")
