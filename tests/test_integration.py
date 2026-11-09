from __future__ import annotations

from typing import Any

import pytest
from debug_toolbar.toolbar import DebugToolbar
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import Client, override_settings
from django.urls import reverse

from debug_toolbar_hijack.panels import HijackPanel
from tests.utils import stats

pytestmark = pytest.mark.django_db


@override_settings(
    DEBUG_TOOLBAR_CONFIG={
        "IS_RUNNING_TESTS": False,
        # pytest-django forces DEBUG=False, which hides the toolbar by default.
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }
)
def test_acquire_then_panel_shows_hijack(client: Client, admin_user: User) -> None:
    alice = User.objects.create_user("alice")
    client.force_login(admin_user)

    response = client.post(
        reverse("hijack:acquire"), {"user_pk": alice.pk, "next": "/page/"}
    )
    assert response.status_code == 302
    assert response["Location"] == "/page/"

    toolbars: list[DebugToolbar] = []

    def capture(sender: HttpRequest, toolbar: DebugToolbar, **kwargs: Any) -> None:
        toolbars.append(toolbar)

    DebugToolbar._created.connect(capture)
    try:
        response = client.get("/page/")
    finally:
        DebugToolbar._created.disconnect(capture)

    assert response.status_code == 200
    assert b"djDebug" in response.content
    (toolbar,) = toolbars
    panel = toolbar.get_panel_by_id("HijackPanel")
    assert isinstance(panel, HijackPanel)
    data = stats(panel)
    assert data["is_hijacked"] is True
    assert data["current_user"] == "alice"
    assert data["hijack_history"] == ["admin"]
    assert "Currently working as <strong>alice</strong>." in panel.content
