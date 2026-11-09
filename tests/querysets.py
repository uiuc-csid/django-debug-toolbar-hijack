"""Custom ``HIJACK_USER_QUERYSET`` factories used by the tests."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import QuerySet


def staff_only(*, user: AbstractBaseUser | AnonymousUser) -> QuerySet[User, Any]:
    staff = User.objects.filter(is_staff=True)
    return staff if user.pk is None else staff.exclude(pk=user.pk)
