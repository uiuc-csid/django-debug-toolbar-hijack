"""Views mounted under the debug toolbar's ``djdt`` namespace."""

from __future__ import annotations

from debug_toolbar.decorators import require_show_toolbar
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from debug_toolbar_hijack.panels import (
    HijackPanel,
    get_hijackable_users,
    serialize_users,
)
from debug_toolbar_hijack.search import search_users as filter_users


# require_show_toolbar is unannotated in django-debug-toolbar.
@require_show_toolbar  # type: ignore[untyped-decorator]
@require_GET
def search_users(request: HttpRequest, panel_class: type[HijackPanel]) -> JsonResponse:
    """Return the hijackable users matching ``?q=`` as JSON.

    Results start from the same ``HIJACK_USER_QUERYSET`` as the panel, are
    filtered with the user model's admin search, sorted by ``USERNAME_FIELD``
    and capped at the panel's ``user_limit``. Anonymous users get no results.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return JsonResponse({"users": [], "truncated": False})

    queryset = filter_users(
        request,
        get_hijackable_users(user),
        request.GET.get("q", ""),
        panel_class.admin_site,
    )
    limit = panel_class.user_limit
    users, truncated = serialize_users(queryset[: limit + 1], limit)
    return JsonResponse({"users": users, "truncated": truncated})
