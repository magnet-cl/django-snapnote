import pytest


def test_button_rendered_for_user(user_client):
    html = user_client.get("/").content.decode()
    assert 'id="snapnote-root"' in html
    assert "snapnote/snapnote.js" in html and "snapnote-props" in html
    assert "/snapnote/report/" in html


def test_button_hidden_for_anonymous(client):
    assert b"snapnote-root" not in client.get("/").content


def test_button_hidden_without_permission(user_client, settings):
    settings.SNAPNOTE_CAN_REPORT = "tests.helpers.nobody"
    assert b"snapnote-root" not in user_client.get("/").content


def test_auto_inject(user_client, settings):
    settings.SNAPNOTE_AUTO_INJECT = False
    assert b"snapnote-root" not in user_client.get("/plain/").content
    settings.SNAPNOTE_AUTO_INJECT = True
    assert user_client.get("/plain/").content.count(b'id="snapnote-root"') == 1
    assert user_client.get("/").content.count(b'id="snapnote-root"') == 1  # not injected twice


def test_purge_and_checks(make_ticket, png, settings):
    from datetime import timedelta

    from django.core.management import call_command
    from django.core.management.base import SystemCheckError  # noqa: F401
    from django.utils import timezone

    from snapnote.models import Ticket

    old = make_ticket(screenshot=png())
    Ticket.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))
    make_ticket()
    call_command("snapnote_purge", older_than=30, dry_run=True)
    assert Ticket.objects.count() == 2
    call_command("snapnote_purge", older_than=30)
    assert Ticket.objects.count() == 1


def test_unaccent_warning_only_without_postgres(settings):
    from django.core.checks import run_checks
    from django.db import connection

    settings.SNAPNOTE_SEARCH_UNACCENT = True
    warned = any(m.id == "snapnote.W001" for m in run_checks())
    assert warned == (connection.vendor != "postgresql")


def _props(response):
    import json
    import re

    html = response.content.decode()
    return json.loads(re.search(r'id="snapnote-props"[^>]*>(.*?)</script>', html, re.S).group(1))


def test_props_include_csrf_token(user_client):
    assert _props(user_client.get("/"))["csrf_token"]


@pytest.mark.parametrize("option", ["CSRF_COOKIE_HTTPONLY", "CSRF_USE_SESSIONS"])
def test_report_works_without_js_readable_cookie_using_props_token(user, settings, option):
    from django.test import Client

    setattr(settings, option, True)
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    token = _props(client.get("/"))["csrf_token"]
    data = {"title": "t", "page_url": "http://testserver/"}
    assert client.post("/snapnote/report/", data, HTTP_X_CSRFTOKEN=token).status_code == 201
    assert client.post("/snapnote/report/", data).status_code == 403
