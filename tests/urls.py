from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import include, path


def page(request: HttpRequest) -> HttpResponse:
    return HttpResponse("<html><body><p>Page</p></body></html>")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("hijack/", include("hijack.urls")),
    path("page/", page),
    # Not debug_toolbar_urls(): it returns [] when DEBUG is False, and
    # pytest-django forces DEBUG=False.
    path("__debug__/", include("debug_toolbar.urls")),
]
