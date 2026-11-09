from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, User

from debug_toolbar_hijack.users import superusers_only

pytestmark = pytest.mark.django_db


def test_superuser_gets_other_active_users(admin_user: User) -> None:
    alice = User.objects.create_user("alice")
    bob = User.objects.create_user("bob", is_staff=True)
    User.objects.create_user("inactive", is_active=False)

    result = set(superusers_only(user=admin_user))

    assert result == {alice, bob}


def test_inactive_superuser_gets_none() -> None:
    root = User.objects.create_superuser("root", is_active=False)
    User.objects.create_user("alice")

    assert not superusers_only(user=root).exists()


@pytest.mark.parametrize("is_staff", [True, False], ids=["staff", "regular"])
def test_non_superusers_get_none(is_staff: bool) -> None:
    user = User.objects.create_user("someone", is_staff=is_staff)
    User.objects.create_user("alice")

    assert not superusers_only(user=user).exists()


def test_anonymous_gets_none() -> None:
    User.objects.create_user("alice")

    assert not superusers_only(user=AnonymousUser()).exists()
