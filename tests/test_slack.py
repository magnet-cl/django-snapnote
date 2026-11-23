import json
from unittest import mock

from django.core.checks import run_checks

from snapnote import notifiers

HOOK = "https://hooks.slack.com/services/T000/B000/SECRETSECRET"


def _post(ticket, url="https://x.example.com/t/1/"):
    with mock.patch("urllib.request.urlopen") as urlopen:
        notifiers.slack(ticket, url)
    request = urlopen.call_args.args[0]
    return request, json.loads(request.data)["text"]


def test_posts_summary_to_webhook(settings, make_ticket):
    settings.SNAPNOTE_SLACK_WEBHOOK_URL = HOOK
    request, text = _post(make_ticket(title="Broken", description="It fails"))
    assert request.full_url == HOOK
    assert "*Broken*" in text and "It fails" in text
    assert "<https://x.example.com/t/1/|Snapnote ticket #" in text


def test_untrusted_text_is_escaped(settings, make_ticket):
    settings.SNAPNOTE_SLACK_WEBHOOK_URL = HOOK
    ticket = make_ticket(
        title="<!channel> hi",
        description="<@U1> <https://evil|click>",
        page_url="javascript:alert(1)",
    )
    _, text = _post(ticket)
    assert "<!channel>" not in text and "&lt;!channel&gt;" in text
    assert "<@U1>" not in text and "<https://evil|click>" not in text
    assert "<javascript:" not in text


def test_failure_does_not_leak_webhook(settings, make_ticket):
    settings.SNAPNOTE_SLACK_WEBHOOK_URL = HOOK
    settings.SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.slack"]
    with mock.patch("urllib.request.urlopen", side_effect=OSError(f"boom {HOOK}")):
        try:
            notifiers.slack(make_ticket(), "")
        except RuntimeError as exc:
            assert "SECRETSECRET" not in str(exc) and exc.__cause__ is None
        else:
            raise AssertionError("expected RuntimeError")
        notifiers.run_notifiers(None, make_ticket(), "")  # contained


def test_check_warns_without_webhook(settings):
    settings.SNAPNOTE_NOTIFIERS = ["snapnote.notifiers.slack"]
    assert [m for m in run_checks() if m.id == "snapnote.W003"]
    settings.SNAPNOTE_SLACK_WEBHOOK_URL = HOOK
    assert not [m for m in run_checks() if m.id == "snapnote.W003"]


def test_http_error_body_does_not_leak_webhook(settings, make_ticket):
    import io
    import urllib.error

    settings.SNAPNOTE_SLACK_WEBHOOK_URL = HOOK
    error = urllib.error.HTTPError(HOOK, 404, "Not Found", {}, io.BytesIO(f"no {HOOK}".encode()))
    with mock.patch("urllib.request.urlopen", side_effect=error):
        try:
            notifiers.slack(make_ticket(), "")
        except RuntimeError as exc:
            assert "HTTP 404" in str(exc)
            assert "SECRETSECRET" not in str(exc) and HOOK not in str(exc)
        else:
            raise AssertionError("expected RuntimeError")


def test_long_description_is_truncated(settings, make_ticket):
    settings.SNAPNOTE_SLACK_WEBHOOK_URL = HOOK
    _, text = _post(make_ticket(description="x" * 2000))
    assert "x" * 500 + "..." in text and "x" * 501 not in text


def test_reporter_is_optional_and_needs_no_email(settings, make_ticket, user):
    settings.SNAPNOTE_SLACK_WEBHOOK_URL = HOOK
    _, text = _post(make_ticket(reported_by=user))
    assert f"Reported by: {user}" in text
    _, text = _post(make_ticket(reported_by=None))
    assert "Reported by" not in text
