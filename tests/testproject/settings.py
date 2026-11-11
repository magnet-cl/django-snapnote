import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = "test"
DEBUG = bool(os.environ.get("SNAPNOTE_E2E"))
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "snapnote",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "snapnote.middleware.AutoInjectMiddleware",
]
ROOT_URLCONF = "tests.testproject.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
_db = os.environ.get("SNAPNOTE_TEST_DB", "sqlite")
if _db == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "snapnote",
            "USER": os.environ.get("PGUSER", "postgres"),
            "PASSWORD": os.environ.get("PGPASSWORD", ""),
            "HOST": os.environ.get("PGHOST", "localhost"),
        }
    }
    INSTALLED_APPS.append("django.contrib.postgres")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SNAPNOTE_E2E_DB", ":memory:"),
        }
    }
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STATIC_URL = "/static/"
MEDIA_ROOT = tempfile.mkdtemp(prefix="snapnote-media-")
MEDIA_URL = "/media/"
LOGIN_URL = "/login/"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
if os.environ.get("SNAPNOTE_TEST_USER") == "custom":
    INSTALLED_APPS.append("tests.testproject.hostapp")
    AUTH_USER_MODEL = "hostapp.CustomUser"
