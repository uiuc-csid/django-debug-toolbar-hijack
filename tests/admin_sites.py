"""Admin sites with different user ``ModelAdmin`` setups for the search tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.http import HttpRequest

# ModelAdmin is only generic in django-stubs.
if TYPE_CHECKING:
    UserAdminBase = admin.ModelAdmin[User]
else:
    UserAdminBase = admin.ModelAdmin


class EmailSearchUserAdmin(UserAdminBase):
    search_fields = ("email",)


class OverrideSearchUserAdmin(UserAdminBase):
    search_fields = ("username",)

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet[Any], search_term: str
    ) -> tuple[QuerySet[User], bool]:
        return queryset.filter(first_name__iexact=search_term), True


class NoSearchUserAdmin(UserAdminBase):
    pass


email_site = admin.AdminSite(name="email_site")
email_site.register(User, EmailSearchUserAdmin)

override_site = admin.AdminSite(name="override_site")
override_site.register(User, OverrideSearchUserAdmin)

no_search_site = admin.AdminSite(name="no_search_site")
no_search_site.register(User, NoSearchUserAdmin)

unregistered_site = admin.AdminSite(name="unregistered_site")
