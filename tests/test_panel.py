from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet
from django.test import override_settings
from django.urls import reverse

from debug_toolbar_hijack.panels import HijackPanel, get_user_queryset_factory
from debug_toolbar_hijack.users import superusers_only
from tests.testapp.models import EmailUser
from tests.utils import MakePanel, stats

pytestmark = pytest.mark.django_db


def labels(panel: HijackPanel) -> list[str]:
    return [user["label"] for user in stats(panel)["users"]]


# Queryset resolution


def test_fallback_when_setting_unset() -> None:
    assert not hasattr(settings, "HIJACK_USER_QUERYSET")
    assert get_user_queryset_factory() is superusers_only


def test_fallback_lists_other_active_users(
    make_panel: MakePanel, admin_user: User
) -> None:
    User.objects.create_user("bob")
    User.objects.create_user("alice")
    User.objects.create_user("inactive", is_active=False)

    assert labels(make_panel(admin_user)) == ["alice", "bob"]


def test_fallback_lists_nothing_for_staff(make_panel: MakePanel) -> None:
    staff = User.objects.create_user("staff", is_staff=True)
    User.objects.create_user("alice")

    assert stats(make_panel(staff))["users"] == []


@override_settings(HIJACK_USER_QUERYSET="tests.querysets.staff_only")
def test_dotted_path_setting(make_panel: MakePanel) -> None:
    regular = User.objects.create_user("regular")
    User.objects.create_user("staff", is_staff=True)

    assert labels(make_panel(regular)) == ["staff"]


def test_callable_setting(make_panel: MakePanel) -> None:
    calls: list[AbstractBaseUser | AnonymousUser] = []

    def factory(*, user: AbstractBaseUser | AnonymousUser) -> QuerySet[User, Any]:
        calls.append(user)
        return User.objects.filter(username="target")

    regular = User.objects.create_user("regular")
    User.objects.create_user("target")

    with override_settings(HIJACK_USER_QUERYSET=factory):
        assert labels(make_panel(regular)) == ["target"]
    assert calls == [regular]


@override_settings(HIJACK_USER_QUERYSET=42)
def test_invalid_setting() -> None:
    with pytest.raises(ImproperlyConfigured):
        get_user_queryset_factory()


def test_orders_by_custom_username_field(
    make_panel: MakePanel, admin_user: User
) -> None:
    """A user model without ``username`` sorts by its ``USERNAME_FIELD``."""
    for email in ["carol@example.com", "alice@example.com", "bob@example.com"]:
        EmailUser.objects.create(email=email)

    with (
        override_settings(HIJACK_USER_QUERYSET=lambda *, user: EmailUser.objects.all()),
        mock.patch(
            "debug_toolbar_hijack.panels.get_user_model", return_value=EmailUser
        ),
    ):
        panel = make_panel(admin_user)

    assert labels(panel) == [
        "alice@example.com",
        "bob@example.com",
        "carol@example.com",
    ]


# Cap


def test_cap_sets_truncated(
    make_panel: MakePanel, admin_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(HijackPanel, "user_limit", 2)
    for name in ["a", "b", "c"]:
        User.objects.create_user(name)

    panel = make_panel(admin_user)

    assert labels(panel) == ["a", "b"]
    assert stats(panel)["truncated"] is True
    assert "Showing the first 2 users." in panel.content


def test_at_cap_is_not_truncated(
    make_panel: MakePanel, admin_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(HijackPanel, "user_limit", 2)
    for name in ["a", "b"]:
        User.objects.create_user(name)

    panel = make_panel(admin_user)

    assert stats(panel)["truncated"] is False
    assert panel.nav_subtitle == "2 hijackable"
    assert "Showing the first" not in panel.content


def test_default_cap_subtitle(make_panel: MakePanel, admin_user: User) -> None:
    User.objects.bulk_create(User(username=f"user{i:03}") for i in range(101))

    panel = make_panel(admin_user)

    assert stats(panel)["user_count"] == 100
    assert stats(panel)["truncated"] is True
    assert panel.nav_subtitle == "100+ hijackable"


# Request handling


def test_anonymous_gets_empty_list(make_panel: MakePanel) -> None:
    User.objects.create_user("alice")

    panel = make_panel(AnonymousUser())

    assert stats(panel)["users"] == []
    assert stats(panel)["current_user"] == ""
    assert panel.nav_subtitle == "0 hijackable"
    assert "No users available to hijack." in panel.content


def test_history_resolves_labels(make_panel: MakePanel, admin_user: User) -> None:
    alice = User.objects.create_user("alice")

    panel = make_panel(alice, history=[str(admin_user.pk), "999999"])

    assert stats(panel)["is_hijacked"] is True
    assert stats(panel)["current_user"] == "alice"
    assert stats(panel)["hijack_history"] == ["admin", "999999"]


def test_not_hijacked_without_history(make_panel: MakePanel, admin_user: User) -> None:
    panel = make_panel(admin_user)

    assert stats(panel)["is_hijacked"] is False
    assert stats(panel)["hijack_history"] == []
    assert "Not currently impersonating anyone." in panel.content


def test_urls_and_csrf_token(make_panel: MakePanel, admin_user: User) -> None:
    panel = make_panel(admin_user, path="/some/page/?x=1")
    data = stats(panel)

    assert data["acquire_url"] == reverse("hijack:acquire")
    assert data["release_url"] == reverse("hijack:release")
    assert data["next"] == "/some/page/?x=1"
    assert data["csrf_token"]


def test_template_renders(make_panel: MakePanel, admin_user: User) -> None:
    alice = User.objects.create_user("alice")
    bob = User.objects.create_user("bob")

    panel = make_panel(alice, history=[str(admin_user.pk)])
    content = panel.content
    data = stats(panel)

    assert "Currently working as <strong>alice</strong>." in content
    assert "Hijack history: admin" in content
    assert f'action="{data["release_url"]}"' in content
    assert f'action="{data["acquire_url"]}"' not in content  # alice isn't a superuser
    assert data["csrf_token"] in content
    assert 'value="/some/page/?x=1"' in content

    panel = make_panel(admin_user)
    content = panel.content
    data = stats(panel)
    assert f'action="{data["acquire_url"]}"' in content
    assert f'name="user_pk" value="{bob.pk}"' in content
    assert "<td>bob</td>" in content
