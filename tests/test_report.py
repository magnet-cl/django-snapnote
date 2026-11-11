import pytest
from django.core import mail
from django.test import Client

from snapnote import conf
from snapnote.models import Ticket

from .conftest import png_bytes

URL = "/snapnote/report/"


def payload(png, **extra):
    data = {
        "title": "Broken",
        "description": "d",
        "page_url": "http://testserver/x/",
        "screenshot": png(),
        "annotations": png("a.png"),
    }
    data.update(extra)
    return data


def test_report_with_files(user_client, png, user):
    response = user_client.post(URL, payload(png))
    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"]}  # files are not echoed back
    ticket = Ticket.objects.get(pk=body["id"])
    assert ticket.reported_by == user
    assert ticket.screenshot and ticket.annotations


def test_report_without_files(user_client):
    data = {"title": "t", "page_url": "https://a.b/"}
    assert user_client.post(URL, data).status_code == 201


def test_title_required(user_client, png):
    response = user_client.post(URL, payload(png, title=""))
    assert response.status_code == 400
    assert "title" in response.json()["errors"]


def test_anonymous_forbidden(client, png):
    assert client.post(URL, payload(png)).status_code == 403


def test_get_not_allowed(user_client):
    assert user_client.get(URL).status_code == 405


def test_custom_can_report(user_client, png, settings):
    settings.SNAPNOTE_CAN_REPORT = "tests.helpers.nobody"
    assert user_client.post(URL, payload(png)).status_code == 403


@pytest.mark.parametrize("bad", ["javascript:alert(1)", "ftp://x/", "/relative", ""])
def test_invalid_page_url_scheme(user_client, png, bad):
    response = user_client.post(URL, payload(png, page_url=bad))
    assert response.status_code == 400
    assert "page_url" in response.json()["errors"]


def test_size_limit(user_client, png, settings):
    settings.SNAPNOTE_MAX_UPLOAD_MB = 0.0001
    assert user_client.post(URL, payload(png, screenshot=png(size=(300, 300)))).status_code == 400


def test_dimension_limit(user_client, png, settings):
    settings.SNAPNOTE_MAX_DIMENSION = 15
    assert user_client.post(URL, payload(png)).status_code == 400


def test_rejects_svg_and_fake_images(user_client, png):
    from django.core.files.uploadedfile import SimpleUploadedFile

    svg = SimpleUploadedFile("a.png", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/png")
    assert user_client.post(URL, payload(png, screenshot=svg)).status_code == 400


def test_reencodes_and_strips_trailing_payload(user_client, png):
    from django.core.files.uploadedfile import SimpleUploadedFile

    dirty = SimpleUploadedFile("a.png", png_bytes() + b"<?php evil ?>", "image/png")
    response = user_client.post(URL, payload(png, screenshot=dirty))
    assert response.status_code == 201
    ticket = Ticket.objects.get(pk=response.json()["id"])
    assert b"evil" not in ticket.screenshot.read()


def test_throttle(user_client, settings):
    settings.SNAPNOTE_THROTTLE = "2/hour"
    data = {"title": "t", "page_url": "http://a/"}
    assert [user_client.post(URL, data).status_code for _ in range(3)] == [201, 201, 429]


def test_csrf_without_prior_cookie(user, png):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post(URL, payload(png)).status_code == 403  # no token
    page = client.get("/")
    token = page.cookies["csrftoken"].value  # the tag sets the cookie
    assert client.post(URL, payload(png), HTTP_X_CSRFTOKEN=token).status_code == 201
    assert client.post(URL, payload(png), HTTP_X_CSRFTOKEN="bad").status_code == 403


def test_notifier_receives_ticket_and_failure_is_harmless(
    user_client, settings, django_capture_on_commit_callbacks
):
    calls = []
    from tests import helpers

    helpers.calls = calls
    settings.SNAPNOTE_NOTIFIERS = ["tests.helpers.failing", "tests.helpers.record"]
    with django_capture_on_commit_callbacks(execute=True):
        response = user_client.post(URL, {"title": "t", "page_url": "http://a/"})
    assert response.status_code == 201
    assert len(calls) == 1
    ticket, url = calls[0]
    assert ticket.title == "t" and url.startswith("http://testserver/snapnote/")


def test_email_notifier(user_client, settings, django_capture_on_commit_callbacks):
    settings.SNAPNOTE_NOTIFY_EMAILS = ["a@example.com"]
    with django_capture_on_commit_callbacks(execute=True):
        user_client.post(URL, {"title": "t", "page_url": "http://a/"})
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["a@example.com"]


def test_email_notifier_noop_by_default(user_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        user_client.post(URL, {"title": "t", "page_url": "http://a/"})
    assert mail.outbox == []


def test_conf_defaults():
    assert conf.get("THROTTLE") == "10/hour"
