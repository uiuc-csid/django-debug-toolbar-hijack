"""Default user querysets for ``settings.HIJACK_USER_QUERYSET``."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet


def superusers_only(
    *, user: AbstractBaseUser | AnonymousUser
) -> QuerySet[AbstractBaseUser, Any]:
    """Mirror ``hijack.permissions.superusers_only`` as a queryset.

    Active superusers may hijack every other active user. Everyone else gets an
    empty queryset. Unlike hijack's permission check, the current user is left
    out, since hijacking yourself is never useful from a list.
    """
    user_model = get_user_model()
    if not (user.is_active and getattr(user, "is_superuser", False)):
        return user_model._default_manager.none()
    return user_model._default_manager.filter(is_active=True).exclude(pk=user.pk)
