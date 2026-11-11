from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.template import engines
from django.urls import include, path


def home(request):
    return HttpResponse(
        engines["django"].from_string("{% extends 'host_base.html' %}").render({}, request)
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("snapnote/", include("snapnote.urls")),
    path("plain/", lambda r: HttpResponse("<html><body>plain</body></html>")),
    path("", home),
]


# Only used by the browser smoke test (frontend/e2e).
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.auth import get_user_model, login
    from django.shortcuts import redirect

    def e2e_login(request):
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username="e2e", defaults={"is_staff": True, "is_superuser": True}
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("/")

    urlpatterns += [path("e2e-login/", e2e_login)]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
