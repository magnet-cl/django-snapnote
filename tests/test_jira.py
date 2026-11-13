import json
from unittest import mock

import pytest
from django.core.checks import run_checks

from snapnote import notifiers


@pytest.fixture
def jira(settings):
    settings.SNAPNOTE_JIRA_URL = "https://acme.atlassian.net/"
    settings.SNAPNOTE_JIRA_EMAIL = "bot@acme.com"
    settings.SNAPNOTE_JIRA_API_TOKEN = "secret"
    settings.SNAPNOTE_JIRA_PROJECT = "APP"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.body).encode()


def fake_urlopen(calls, fail_attachments=False):
    def urlopen(request, timeout=None):
        calls.append(request)
        if "attachments" in request.full_url and fail_attachments:
            raise OSError("boom")
        return FakeResponse({"key": "APP-7"})

    return urlopen


def test_creates_issue_and_attaches_images(jira, make_ticket, png):
    ticket = make_ticket(
        title="Broken", description="It fails", screenshot=png(), annotations=png("a.png")
    )
    calls = []
    with mock.patch("urllib.request.urlopen", fake_urlopen(calls)):
        key = notifiers.jira_issue(ticket, "http://testserver/snapnote/1/")
    assert key == "APP-7"
    ticket.refresh_from_db()
    assert ticket.jira_key == "APP-7"
    assert ticket.jira_url == "https://acme.atlassian.net/browse/APP-7"
    create, shot, ann = calls
    assert create.full_url == "https://acme.atlassian.net/rest/api/3/issue"
    assert create.get_header("Authorization").startswith("Basic ")
    fields = json.loads(create.data)["fields"]
    assert fields["project"] == {"key": "APP"} and fields["issuetype"] == {"name": "Bug"}
    assert fields["summary"] == "Broken" and fields["labels"] == ["snapnote"]
    text = json.dumps(fields["description"])
    assert "It fails" in text and "http://testserver/snapnote/1/" in text
    assert shot.full_url.endswith("/issue/APP-7/attachments")
    assert shot.get_header("X-atlassian-token") == "no-check"
    assert ann.full_url.endswith("/issue/APP-7/attachments")


def test_no_attachments_when_disabled_or_absent(jira, settings, make_ticket, png):
    settings.SNAPNOTE_JIRA_ATTACH_IMAGES = False
    calls = []
    with mock.patch("urllib.request.urlopen", fake_urlopen(calls)):
        notifiers.jira_issue(make_ticket(screenshot=png()), "")
    assert len(calls) == 1


def test_attachment_failure_does_not_fail_notifier(jira, make_ticket, png):
    calls = []
    with mock.patch("urllib.request.urlopen", fake_urlopen(calls, fail_attachments=True)):
        assert notifiers.jira_issue(make_ticket(screenshot=png()), "") == "APP-7"


def test_javascript_page_url_is_not_a_link(jira, make_ticket):
    calls = []
    with mock.patch("urllib.request.urlopen", fake_urlopen(calls)):
        notifiers.jira_issue(make_ticket(page_url="javascript:alert(1)"), "")
    assert '"link"' not in calls[0].data.decode()


def test_jira_failure_is_contained_by_runner(jira, settings, make_ticket):
    settings.SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.jira_issue"]
    with mock.patch("urllib.request.urlopen", side_effect=OSError("down")):
        notifiers.run_notifiers(None, make_ticket(), "")  # must not raise


def test_check_warns_when_misconfigured(settings):
    settings.SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.jira_issue"]
    warnings = [m for m in run_checks() if m.id == "snapnote.W002"]
    assert warnings and "SNAPNOTE_JIRA_URL" in warnings[0].hint


def test_check_silent_when_configured(jira, settings):
    settings.SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.jira_issue"]
    assert not [m for m in run_checks() if m.id == "snapnote.W002"]


def test_key_is_saved_even_if_attachments_fail(jira, make_ticket, png):
    ticket = make_ticket(screenshot=png())
    with mock.patch("urllib.request.urlopen", fake_urlopen([], fail_attachments=True)):
        notifiers.jira_issue(ticket, "")
    ticket.refresh_from_db()
    assert ticket.jira_key == "APP-7"


def test_no_key_when_jira_fails(jira, make_ticket):
    ticket = make_ticket()
    with mock.patch("urllib.request.urlopen", side_effect=OSError("down")):
        notifiers.run_notifiers(None, ticket, "")
    ticket.refresh_from_db()
    assert ticket.jira_key == "" and ticket.jira_url == ""


def test_key_shown_in_views_admin_and_export(jira, manager_client, make_ticket, tmp_path):
    from django.core.management import call_command

    ticket = make_ticket(jira_key="APP-7")
    link = 'href="https://acme.atlassian.net/browse/APP-7"'
    assert link in manager_client.get(ticket.get_absolute_url()).content.decode()
    assert link in manager_client.get("/snapnote/").content.decode()
    assert list(type(ticket).objects.search("APP-7")) == [ticket]
    call_command("snapnote_export", ticket.pk, output=str(tmp_path))
    folder = tmp_path / f"ticket-{ticket.pk}"
    assert "APP-7" in (folder / "ticket.md").read_text()
    assert '"jira_key": "APP-7"' in (folder / "ticket.json").read_text()
