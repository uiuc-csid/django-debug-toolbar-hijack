from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from debug_toolbar import middleware
from debug_toolbar.toolbar import DebugToolbar
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from debug_toolbar_hijack.panels import HijackPanel
from tests.utils import MakePanel


def _get_response(request: HttpRequest) -> HttpResponse:
    return HttpResponse("<html><body></body></html>")


@pytest.fixture(autouse=True)
def _reset_show_toolbar_cache() -> Iterator[None]:
    """Forget the cached ``SHOW_TOOLBAR_CALLBACK``.

    django-debug-toolbar caches the resolved callback and doesn't clear it when
    ``DEBUG_TOOLBAR_CONFIG`` is overridden, so tests would leak it.
    """
    cached = getattr(middleware, "show_toolbar_func_or_path", None)
    clear = getattr(cached, "cache_clear", lambda: None)
    clear()
    yield
    clear()


@pytest.fixture
def make_panel(rf: RequestFactory) -> MakePanel:
    """Build a toolbar for a request and run the hijack panel over it."""

    def make(
        user: User | AnonymousUser | None = None,
        history: list[Any] | None = None,
        path: str = "/some/page/?x=1",
    ) -> HijackPanel:
        request = rf.get(path)
        request.user = user if user is not None else AnonymousUser()
        session = SessionStore()
        if history is not None:
            session["hijack_history"] = history
        request.session = session
        toolbar = DebugToolbar(request, _get_response)
        panel = toolbar.get_panel_by_id("HijackPanel")
        assert isinstance(panel, HijackPanel)
        panel.generate_stats(request, _get_response(request))
        return panel

    return make
