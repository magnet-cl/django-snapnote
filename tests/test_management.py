from django.urls import reverse

from snapnote.models import Ticket


def test_list_requires_login(client):
    response = client.get(reverse("snapnote:ticket_list"))
    assert response.status_code == 302 and response["Location"].startswith("/login/")


def test_list_forbidden_without_permission(user_client):
    assert user_client.get(reverse("snapnote:ticket_list")).status_code == 403


def test_list_search_and_status(manager_client, make_ticket):
    make_ticket(title="alpha")
    closed = make_ticket(title="beta")
    closed.close(None)
    url = reverse("snapnote:ticket_list")
    assert [t.title for t in manager_client.get(url, {"q": "alp"}).context["object_list"]] == [
        "alpha"
    ]
    assert [
        t.title for t in manager_client.get(url, {"status": "closed"}).context["object_list"]
    ] == ["beta"]


def test_close_reopen_and_audit(manager_client, manager, make_ticket):
    ticket = make_ticket()
    response = manager_client.post(reverse("snapnote:ticket_close", args=[ticket.pk]))
    assert response["Location"] == ticket.get_absolute_url()
    ticket.refresh_from_db()
    assert ticket.status == "closed" and ticket.closed_by == manager and ticket.closed_at
    manager_client.post(reverse("snapnote:ticket_reopen", args=[ticket.pk]))
    ticket.refresh_from_db()
    assert ticket.status == "open" and ticket.closed_at is None


def test_status_change_needs_change_perm(client, db, make_ticket):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission

    User = get_user_model()
    viewer = User.objects.create_user(**{User.USERNAME_FIELD: "viewer"}, password="x")
    viewer.user_permissions.add(Permission.objects.get(codename="view_ticket"))
    client.force_login(viewer)
    ticket = make_ticket()
    assert client.post(reverse("snapnote:ticket_close", args=[ticket.pk])).status_code == 403
    page = client.get(ticket.get_absolute_url())
    assert page.status_code == 200 and b"snapnote-btn-ok" not in page.content


def test_close_is_post_only(manager_client, make_ticket):
    ticket = make_ticket()
    assert manager_client.get(reverse("snapnote:ticket_close", args=[ticket.pk])).status_code == 405


def test_annotation_switch_only_with_annotations(manager_client, make_ticket, png):
    plain = make_ticket(screenshot=png())
    assert b"snapnote-ann-toggle" not in manager_client.get(plain.get_absolute_url()).content
    both = make_ticket(screenshot=png(), annotations=png("a.png"))
    assert b"snapnote-ann-toggle" in manager_client.get(both.get_absolute_url()).content


def test_delete(manager_client, make_ticket):
    ticket = make_ticket()
    url = reverse("snapnote:ticket_delete", args=[ticket.pk])
    assert manager_client.get(url).status_code == 200
    assert manager_client.post(url).status_code == 302
    assert not Ticket.objects.exists()


def test_javascript_page_url_is_not_linked(manager_client, make_ticket):
    ticket = make_ticket(page_url="javascript:alert(1)")
    assert b'href="javascript' not in manager_client.get(ticket.get_absolute_url()).content


def test_alternate_base_template(manager_client, settings, make_ticket):
    settings.SNAPNOTE_BASE_TEMPLATE = "alt_base.html"
    make_ticket()
    assert b'id="alt-base"' in manager_client.get(reverse("snapnote:ticket_list")).content


def test_management_views_disabled(manager_client, settings, make_ticket):
    settings.SNAPNOTE_ENABLE_MANAGEMENT_VIEWS = False
    ticket = make_ticket()
    assert manager_client.get(reverse("snapnote:ticket_list")).status_code == 404
    assert manager_client.get(ticket.get_absolute_url()).status_code == 404


def test_admin_registered(client, superuser, make_ticket):
    client.force_login(superuser)
    make_ticket()
    assert client.get("/admin/snapnote/ticket/").status_code == 200


def test_pagination_and_superuser_implicit(client, superuser, make_ticket):
    for i in range(30):
        make_ticket(title=f"t{i}")
    client.force_login(superuser)
    response = client.get(reverse("snapnote:ticket_list"), {"page": 2})
    assert response.status_code == 200 and len(response.context["object_list"]) == 5
