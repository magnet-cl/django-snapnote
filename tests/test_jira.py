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


# --- failure visibility and retry -------------------------------------------------------------


def http_error(code=500, body=b'{"errorMessages":["boom"]}'):
    import io
    import urllib.error

    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body))


@pytest.fixture
def jira_on(jira, settings):
    settings.SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.jira_issue"]


def test_failure_is_recorded_without_credentials(jira, settings, make_ticket):
    ticket = make_ticket()
    body = b'{"errorMessages":["bad token secret for bot@acme.com"]}'
    with mock.patch("urllib.request.urlopen", side_effect=http_error(401, body)):
        with pytest.raises(Exception, match="401|err"):
            notifiers.jira_issue(ticket, "")
    ticket.refresh_from_db()
    assert ticket.jira_status == "failed" and ticket.jira_key == ""
    assert ticket.jira_error.startswith("HTTP 401")
    assert "secret" not in ticket.jira_error.replace("bad token secret", "")  # token never leaks
    assert "bot@acme.com" not in ticket.jira_error
    assert len(ticket.jira_error) <= 300


def test_connection_error_and_truncation(jira, make_ticket):
    import urllib.error

    ticket = make_ticket()
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("x" * 1000)):
        notifiers.run_notifiers  # noqa: B018
        with pytest.raises(urllib.error.URLError):
            notifiers.jira_issue(ticket, "")
    ticket.refresh_from_db()
    assert ticket.jira_error.startswith("Connection error") and len(ticket.jira_error) == 300


def test_success_clears_a_previous_error(jira, make_ticket):
    ticket = make_ticket(jira_error="HTTP 500: old")
    with mock.patch("urllib.request.urlopen", fake_urlopen([])):
        notifiers.jira_issue(ticket, "")
    ticket.refresh_from_db()
    assert ticket.jira_status == "ok" and ticket.jira_error == ""


def test_attachment_failure_marks_partial(jira, make_ticket, png):
    ticket = make_ticket(screenshot=png())
    with mock.patch("urllib.request.urlopen", fake_urlopen([], fail_attachments=True)):
        notifiers.jira_issue(ticket, "")
    ticket.refresh_from_db()
    assert ticket.jira_status == "partial" and ticket.jira_key == "APP-7"
    assert ticket.jira_error.startswith("Attachments failed")


def test_report_still_succeeds_and_records_the_error(
    jira_on, user_client, django_capture_on_commit_callbacks
):
    from snapnote.models import Ticket

    with mock.patch("urllib.request.urlopen", side_effect=http_error()):
        with django_capture_on_commit_callbacks(execute=True):
            response = user_client.post(
                "/snapnote/report/", {"title": "t", "page_url": "http://a/"}
            )
    assert response.status_code == 201
    assert Ticket.objects.get().jira_status == "failed"


def test_status_property_and_queryset_filter(make_ticket):
    from snapnote.models import Ticket

    ok = make_ticket(jira_key="A-1")
    partial = make_ticket(jira_key="A-2", jira_error="Attachments failed")
    failed = make_ticket(jira_error="HTTP 500")
    none = make_ticket()
    assert [t.jira_status for t in (ok, partial, failed, none)] == ["ok", "partial", "failed", ""]
    assert set(Ticket.objects.jira("ok")) == {ok, partial}
    assert list(Ticket.objects.jira("failed")) == [failed]
    assert list(Ticket.objects.jira("none")) == [none]
    assert Ticket.objects.jira("").count() == 4


def test_detail_shows_failure_and_retry_button(jira_on, manager_client, make_ticket):
    ticket = make_ticket(jira_error="HTTP 500: boom")
    html = manager_client.get(ticket.get_absolute_url()).content.decode()
    assert "Jira failed" in html and "HTTP 500: boom" in html
    assert f"/snapnote/{ticket.pk}/jira/retry/" in html


def test_retry_button_hidden_without_change_permission(jira_on, client, db, make_ticket):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission

    User = get_user_model()
    viewer = User.objects.create_user(**{User.USERNAME_FIELD: "viewer"}, password="x")
    viewer.user_permissions.add(Permission.objects.get(codename="view_ticket"))
    client.force_login(viewer)
    ticket = make_ticket(jira_error="HTTP 500")
    html = client.get(ticket.get_absolute_url()).content.decode()
    assert "Jira failed" in html and "jira/retry" not in html
    assert client.post(f"/snapnote/{ticket.pk}/jira/retry/").status_code == 403


def test_retry_view_creates_the_issue_once(jira_on, manager_client, make_ticket):
    ticket = make_ticket(jira_error="HTTP 500")
    url = f"/snapnote/{ticket.pk}/jira/retry/"
    calls = []
    with mock.patch("urllib.request.urlopen", fake_urlopen(calls)):
        response = manager_client.post(url)
        manager_client.post(url)  # second click must not create a second issue
    assert response["Location"] == ticket.get_absolute_url()
    ticket.refresh_from_db()
    assert ticket.jira_key == "APP-7" and ticket.jira_error == "" and len(calls) == 1
    assert "http://testserver/snapnote/" in calls[0].data.decode()


def test_retry_view_failure_keeps_the_error(jira_on, manager_client, make_ticket):
    ticket = make_ticket(jira_error="HTTP 500")
    with mock.patch("urllib.request.urlopen", side_effect=http_error(503)):
        assert manager_client.post(f"/snapnote/{ticket.pk}/jira/retry/").status_code == 302
    ticket.refresh_from_db()
    assert ticket.jira_error.startswith("HTTP 503") and ticket.jira_key == ""


def test_retry_view_is_404_when_jira_is_not_configured(manager_client, make_ticket):
    ticket = make_ticket(jira_error="HTTP 500")
    assert manager_client.post(f"/snapnote/{ticket.pk}/jira/retry/").status_code == 404
    assert manager_client.get(f"/snapnote/{ticket.pk}/jira/retry/").status_code in (404, 405)


def test_list_shows_failure_and_filters(jira_on, manager_client, make_ticket):
    make_ticket(title="bad", jira_error="HTTP 500")
    make_ticket(title="good", jira_key="APP-1")
    html = manager_client.get("/snapnote/").content.decode()
    assert "Jira failed" in html
    titles = [
        t.title for t in manager_client.get("/snapnote/", {"jira": "failed"}).context["object_list"]
    ]
    assert titles == ["bad"]


def test_admin_filter(client, superuser, make_ticket):
    client.force_login(superuser)
    make_ticket(title="bad", jira_error="HTTP 500")
    make_ticket(title="good", jira_key="APP-1")
    page = client.get("/admin/snapnote/ticket/", {"jira": "failed"})
    assert page.status_code == 200
    assert [t.title for t in page.context["cl"].result_list] == ["bad"]


def test_retry_command(jira_on, settings, make_ticket):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    settings.SNAPNOTE_BASE_URL = "https://intranet.example.com/"
    bad = make_ticket(jira_error="HTTP 500")
    ok = make_ticket(jira_key="A-1")
    calls = []
    with mock.patch("urllib.request.urlopen", fake_urlopen(calls)):
        call_command("snapnote_retry_jira", dry_run=True)
        assert calls == []
        call_command("snapnote_retry_jira")
    bad.refresh_from_db()
    ok.refresh_from_db()
    assert bad.jira_key == "APP-7" and ok.jira_key == "A-1" and len(calls) == 1
    assert "https://intranet.example.com/snapnote/" in calls[0].data.decode()
    settings.SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.email"]
    with pytest.raises(CommandError):
        call_command("snapnote_retry_jira")
