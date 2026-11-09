"""Filter hijackable users with the user model's admin search."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.module_loading import import_string

if TYPE_CHECKING:
    from django.contrib.admin import AdminSite, ModelAdmin

DEFAULT_ADMIN_SITE = "django.contrib.admin.site"


def get_user_model_admin(
    request: HttpRequest, admin_site: str | AdminSite = DEFAULT_ADMIN_SITE
) -> ModelAdmin[Any] | None:
    """Return the user model's ``ModelAdmin`` when it has search fields.

    ``admin_site`` is an ``AdminSite`` or a dotted path to one. Return ``None``
    when the admin isn't installed, the user model isn't registered on that
    site, or its admin defines no search fields.
    """
    if not apps.is_installed("django.contrib.admin"):
        return None
    site: AdminSite = (
        import_string(admin_site) if isinstance(admin_site, str) else admin_site
    )
    user_model = get_user_model()
    if not site.is_registered(user_model):
        return None
    model_admin: ModelAdmin[Any] = site.get_model_admin(user_model)
    if not model_admin.get_search_fields(request):
        return None
    return model_admin


def fallback_search(queryset: QuerySet[Any, Any], term: str) -> QuerySet[Any, Any]:
    """Match ``term`` against ``USERNAME_FIELD`` and the email field, if any."""
    user_model = get_user_model()
    fields = [user_model.USERNAME_FIELD]
    email_field = user_model.get_email_field_name()
    if email_field not in fields:
        try:
            user_model._meta.get_field(email_field)
        except FieldDoesNotExist:
            pass
        else:
            fields.append(email_field)
    condition = Q()
    for field in fields:
        condition |= Q(**{f"{field}__icontains": term})
    return queryset.filter(condition)


def search_users(
    request: HttpRequest,
    queryset: QuerySet[Any, Any],
    term: str,
    admin_site: str | AdminSite = DEFAULT_ADMIN_SITE,
) -> QuerySet[Any, Any]:
    """Filter ``queryset`` by ``term`` the way the user model's admin would.

    Uses ``ModelAdmin.get_search_results()`` (so ``search_fields`` prefixes and
    custom overrides apply) when the user model is registered on
    ``admin_site`` with search fields, and :func:`fallback_search` otherwise.
    The result is always a subset of ``queryset``.
    """
    term = term.strip()
    if not term:
        return queryset
    model_admin = get_user_model_admin(request, admin_site)
    if model_admin is None:
        return fallback_search(queryset, term)
    results, may_have_duplicates = model_admin.get_search_results(
        request, queryset, term
    )
    if may_have_duplicates:
        results = results.distinct()
    return results
