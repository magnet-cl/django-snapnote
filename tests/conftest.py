import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    cache.clear()


def _make_user(handle, **extra):
    User = get_user_model()
    return User.objects.create_user(**{User.USERNAME_FIELD: handle}, password="x", **extra)


@pytest.fixture
def user(db):
    return _make_user("regular")


@pytest.fixture
def manager(db):
    u = _make_user("manager")
    u.user_permissions.set(Permission.objects.filter(content_type__app_label="snapnote"))
    return u


@pytest.fixture
def superuser(db):
    User = get_user_model()
    return User.objects.create_superuser(**{User.USERNAME_FIELD: "root"}, password="x")


@pytest.fixture
def user_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def manager_client(client, manager):
    client.force_login(manager)
    return client


def png_bytes(size=(20, 10), fmt="PNG", mode="RGBA"):
    buf = io.BytesIO()
    Image.new(mode, size, (255, 0, 0, 128) if mode == "RGBA" else "red").save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def png():
    def make(name="shot.png", **kwargs):
        return SimpleUploadedFile(name, png_bytes(**kwargs), content_type="image/png")

    return make


@pytest.fixture
def make_ticket(db, user):
    from snapnote.models import Ticket

    def make(**kwargs):
        kwargs.setdefault("title", "Broken")
        kwargs.setdefault("page_url", "http://testserver/page/?a=1")
        kwargs.setdefault("reported_by", user)
        return Ticket.objects.create(**kwargs)

    return make
