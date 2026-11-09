"""Demo-only helpers: log every anonymous request in as the demo superuser."""

from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse

DEMO_USERNAME = "admin"


def show_toolbar(request: HttpRequest) -> bool:
    return True


def auto_login(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    def middleware(request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            login(
                request,
                User.objects.get(username=DEMO_USERNAME),
                backend="django.contrib.auth.backends.ModelBackend",
            )
        return get_response(request)

    return middleware
