from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from debug_toolbar.panels import Panel
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from debug_toolbar_hijack.users import superusers_only


class UserQuerysetFactory(Protocol):
    """A callable that returns the users ``user`` may hijack."""

    def __call__(
        self, *, user: AbstractBaseUser | AnonymousUser
    ) -> QuerySet[Any, Any]: ...


def get_user_queryset_factory() -> UserQuerysetFactory:
    """Resolve ``settings.HIJACK_USER_QUERYSET``.

    The setting may be a dotted path or a callable. When it is unset, fall back
    to :func:`debug_toolbar_hijack.users.superusers_only`.
    """
    setting = getattr(settings, "HIJACK_USER_QUERYSET", None)
    if setting is None:
        return superusers_only
    if isinstance(setting, str):
        factory: UserQuerysetFactory = import_string(setting)
        return factory
    if callable(setting):
        return setting  # type: ignore[no-any-return]
    raise ImproperlyConfigured(
        "HIJACK_USER_QUERYSET must be a dotted path or a callable."
    )


def get_hijackable_users(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[Any, Any]:
    """Return the users ``user`` may hijack, sorted by ``USERNAME_FIELD``."""
    factory = get_user_queryset_factory()
    return factory(user=user).order_by(get_user_model().USERNAME_FIELD)


class HijackPanel(Panel):
    """List hijackable users with one-click django-hijack links.

    Pulls the set of impersonatable accounts from the queryset configured by
    ``settings.HIJACK_USER_QUERYSET`` and renders a form per user that POSTs to
    ``hijack:acquire``, so you can impersonate another account straight from the
    debug toolbar. A status bar reflects the current ``hijack_history`` and
    offers a release button while impersonating.
    """

    title = _("Hijack")
    nav_title = _("Hijack")
    template = "debug_toolbar_hijack/panel.html"

    # Cap the listing so a large user table doesn't blow up the panel.
    user_limit = 100

    @property
    def nav_subtitle(self) -> str:
        # Panel.get_stats / record_stats are unannotated in debug_toolbar.
        stats = self.get_stats()  # type: ignore[no-untyped-call]
        count = stats.get("user_count", 0)
        if stats.get("truncated", False):
            return str(_("%(count)d+ hijackable") % {"count": count})
        return str(_("%(count)d hijackable") % {"count": count})

    def generate_stats(self, request: HttpRequest, response: HttpResponse) -> None:
        hijacker = getattr(request, "user", None)
        is_authenticated = hijacker is not None and hijacker.is_authenticated

        session = getattr(request, "session", None)
        history_pks = session.get("hijack_history", []) if session is not None else []
        history = self._resolve_history(history_pks)

        users: list[dict[str, str]] = []
        truncated = False
        if hijacker is not None and is_authenticated:
            # Fetch one extra row to tell whether the list was capped.
            rows = list(get_hijackable_users(hijacker)[: self.user_limit + 1])
            truncated = len(rows) > self.user_limit
            users = [
                {"pk": str(user.pk), "label": str(user)}
                for user in rows[: self.user_limit]
            ]

        self.record_stats(  # type: ignore[no-untyped-call]
            {
                "users": users,
                "user_count": len(users),
                "user_limit": self.user_limit,
                "truncated": truncated,
                "is_hijacked": bool(history_pks),
                "current_user": str(hijacker) if is_authenticated else "",
                "hijack_history": history,
                "csrf_token": get_token(request),
                "acquire_url": reverse("hijack:acquire"),
                "release_url": reverse("hijack:release"),
                "next": request.get_full_path(),
            }
        )

    def _resolve_history(self, history_pks: Sequence[Any]) -> list[str]:
        """Map the session's hijacker pks to display labels, preserving order."""
        if not history_pks:
            return []
        user_model = get_user_model()
        labels = {
            str(user.pk): str(user)
            for user in user_model._default_manager.filter(pk__in=history_pks)
        }
        return [labels.get(str(pk), str(pk)) for pk in history_pks]
