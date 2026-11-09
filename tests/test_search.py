from __future__ import annotations

import json
from typing import Any
from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import Http404, HttpRequest
from django.templatetags.static import static
from django.test import Client, RequestFactory, override_settings
from django.urls import resolve, reverse

from debug_toolbar_hijack import views
from debug_toolbar_hijack.panels import HijackPanel
from debug_toolbar_hijack.search import search_users
from tests.admin_sites import email_site
from tests.testapp.models import EmailUser
from tests.utils import MakePanel, stats

pytestmark = pytest.mark.django_db

SHOW_TOOLBAR = {
    "IS_RUNNING_TESTS": False,
    # pytest-django forces DEBUG=False, which hides the toolbar by default.
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
}


def make_panel_class(admin_site: str) -> type[HijackPanel]:
    return type("CustomHijackPanel", (HijackPanel,), {"admin_site": admin_site})


@pytest.fixture
def people() -> dict[str, User]:
    """Users whose username, email and name match different search terms."""
    return {
        "alice": User.objects.create_user(
            "alice", email="wonderland@example.com", first_name="Ally"
        ),
        "bob": User.objects.create_user(
            "bob", email="builder@example.org", last_name="Smith"
        ),
        "carol": User.objects.create_user(
            "carol", email="carol@example.com", first_name="Ally"
        ),
    }


def usernames(
    admin_user: User, term: str, admin_site: str, rf: RequestFactory
) -> list[str]:
    request = rf.get("/")
    request.user = admin_user
    queryset = User.objects.exclude(pk=admin_user.pk).order_by("username")
    return [u.username for u in search_users(request, queryset, term, admin_site)]


def get_json(
    request: HttpRequest, panel_class: type[HijackPanel] = HijackPanel
) -> dict[str, Any]:
    with override_settings(DEBUG_TOOLBAR_CONFIG=SHOW_TOOLBAR):
        response = views.search_users(request, panel_class=panel_class)
    assert response.status_code == 200
    result: dict[str, Any] = json.loads(response.content)
    return result


def get_labels(request: HttpRequest, **kwargs: Any) -> list[str]:
    return [user["label"] for user in get_json(request, **kwargs)["users"]]


# Admin search fields


@pytest.mark.usefixtures("people")
def test_registered_admin_search_fields(admin_user: User, rf: RequestFactory) -> None:
    site = "tests.admin_sites.email_site"

    assert usernames(admin_user, "wonderland", site, rf) == ["alice"]
    assert usernames(admin_user, "example.com", site, rf) == ["alice", "carol"]
    # search_fields = ["email"], so the username itself doesn't match.
    assert usernames(admin_user, "bob", site, rf) == []


@pytest.mark.usefixtures("people")
def test_default_site_uses_user_admin(admin_user: User, rf: RequestFactory) -> None:
    """``django.contrib.auth``'s ``UserAdmin`` also searches the last name."""
    assert usernames(admin_user, "smith", "django.contrib.admin.site", rf) == ["bob"]


@pytest.mark.usefixtures("people")
def test_get_search_results_override(admin_user: User, rf: RequestFactory) -> None:
    request = rf.get("/")
    request.user = admin_user
    results = search_users(
        request, User.objects.all(), "ally", "tests.admin_sites.override_site"
    )

    assert sorted(u.username for u in results) == ["alice", "carol"]
    # The override reports possible duplicates, so the results are distinct.
    assert results.query.distinct


def test_admin_site_instance(admin_user: User, rf: RequestFactory) -> None:
    User.objects.create_user("alice", email="wonderland@example.com")
    request = rf.get("/")
    request.user = admin_user

    results = search_users(request, User.objects.all(), "wonder", email_site)

    assert [u.username for u in results] == ["alice"]


# Fallback


@pytest.mark.parametrize(
    "site",
    ["tests.admin_sites.unregistered_site", "tests.admin_sites.no_search_site"],
    ids=["unregistered", "no-search-fields"],
)
@pytest.mark.usefixtures("people")
def test_fallback_username_and_email(
    admin_user: User, site: str, rf: RequestFactory
) -> None:
    assert usernames(admin_user, "BOB", site, rf) == ["bob"]
    assert usernames(admin_user, "wonderland", site, rf) == ["alice"]
    assert usernames(admin_user, "example.org", site, rf) == ["bob"]
    # Names aren't part of the fallback.
    assert usernames(admin_user, "smith", site, rf) == []


@pytest.mark.usefixtures("people")
def test_fallback_without_admin_installed(admin_user: User, rf: RequestFactory) -> None:
    with mock.patch(
        "debug_toolbar_hijack.search.apps.is_installed", return_value=False
    ):
        result = usernames(admin_user, "smith", "django.contrib.admin.site", rf)

    assert result == []


def test_fallback_custom_username_field(rf: RequestFactory) -> None:
    """``USERNAME_FIELD`` is the email field; it is searched once."""
    for email in ["alice@example.com", "bob@example.org"]:
        EmailUser.objects.create(email=email)
    request = rf.get("/")

    with mock.patch(
        "debug_toolbar_hijack.search.get_user_model", return_value=EmailUser
    ):
        results = search_users(request, EmailUser.objects.all(), "example.org")

    assert [str(u) for u in results] == ["bob@example.org"]


def test_blank_term_returns_queryset(admin_user: User, rf: RequestFactory) -> None:
    request = rf.get("/")
    queryset = User.objects.all()

    assert search_users(request, queryset, "  ") is queryset


# View


@pytest.mark.usefixtures("people")
def test_view_returns_matches(admin_user: User, rf: RequestFactory) -> None:
    request = rf.get("/", {"q": "ally"})
    request.user = admin_user

    data = get_json(request)

    assert data == {
        "users": [
            {"pk": str(User.objects.get(username=name).pk), "label": name}
            for name in ["alice", "carol"]
        ],
        "truncated": False,
    }


def test_view_stays_within_hijack_queryset(
    admin_user: User, rf: RequestFactory
) -> None:
    User.objects.create_user("match-active")
    User.objects.create_user("match-inactive", is_active=False)
    admin_user.username = "match-admin"
    admin_user.save()
    request = rf.get("/", {"q": "match"})
    request.user = admin_user

    # superusers_only leaves out inactive users and the hijacker.
    assert get_labels(request) == ["match-active"]


@override_settings(HIJACK_USER_QUERYSET="tests.querysets.staff_only")
def test_view_stays_within_custom_queryset(rf: RequestFactory) -> None:
    regular = User.objects.create_user("match-regular")
    User.objects.create_user("match-staff", is_staff=True)
    request = rf.get("/", {"q": "match"})
    request.user = regular

    assert get_labels(request) == ["match-staff"]


def test_view_non_superuser_gets_nothing(rf: RequestFactory) -> None:
    staff = User.objects.create_user("staff", is_staff=True)
    User.objects.create_user("alice")
    request = rf.get("/", {"q": "alice"})
    request.user = staff

    assert get_labels(request) == []


def test_view_anonymous_gets_empty_list(rf: RequestFactory) -> None:
    User.objects.create_user("alice")
    request = rf.get("/", {"q": "alice"})
    request.user = AnonymousUser()

    assert get_json(request) == {"users": [], "truncated": False}


def test_view_cap_sets_truncated(
    admin_user: User, rf: RequestFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(HijackPanel, "user_limit", 2)
    for name in ["match-c", "match-a", "match-b", "other"]:
        User.objects.create_user(name)
    request = rf.get("/", {"q": "match"})
    request.user = admin_user

    data = get_json(request)

    assert [user["label"] for user in data["users"]] == ["match-a", "match-b"]
    assert data["truncated"] is True


def test_view_at_cap_is_not_truncated(
    admin_user: User, rf: RequestFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(HijackPanel, "user_limit", 2)
    for name in ["match-a", "match-b"]:
        User.objects.create_user(name)
    request = rf.get("/", {"q": "match"})
    request.user = admin_user

    assert get_json(request)["truncated"] is False


@pytest.mark.usefixtures("people")
def test_view_custom_admin_site(admin_user: User, rf: RequestFactory) -> None:
    request = rf.get("/", {"q": "example.com"})
    request.user = admin_user

    default = get_labels(request)
    custom = get_labels(
        request, panel_class=make_panel_class("tests.admin_sites.override_site")
    )

    assert default == ["alice", "carol"]
    assert custom == []


@override_settings(
    DEBUG_TOOLBAR_CONFIG={
        "IS_RUNNING_TESTS": False,
        "SHOW_TOOLBAR_CALLBACK": lambda request: False,
    }
)
def test_view_404_when_toolbar_hidden(client: Client, admin_user: User) -> None:
    client.force_login(admin_user)

    response = client.get(reverse("djdt:hijack_search"), {"q": "a"})

    assert response.status_code == 404


def test_view_404_direct_when_toolbar_hidden(
    admin_user: User, rf: RequestFactory
) -> None:
    request = rf.get("/", {"q": "a"})
    request.user = admin_user

    with (
        override_settings(
            DEBUG_TOOLBAR_CONFIG={
                "IS_RUNNING_TESTS": False,
                "SHOW_TOOLBAR_CALLBACK": lambda request: False,
            }
        ),
        pytest.raises(Http404),
    ):
        views.search_users(request, panel_class=HijackPanel)


@override_settings(DEBUG_TOOLBAR_CONFIG=SHOW_TOOLBAR)
@pytest.mark.usefixtures("people")
def test_endpoint_end_to_end(client: Client, admin_user: User) -> None:
    client.force_login(admin_user)

    response = client.get(reverse("djdt:hijack_search"), {"q": "wonderland"})

    assert response.status_code == 200
    assert response.json()["users"] == [
        {"pk": str(User.objects.get(username="alice").pk), "label": "alice"}
    ]


@override_settings(DEBUG_TOOLBAR_CONFIG=SHOW_TOOLBAR)
def test_endpoint_rejects_post(client: Client, admin_user: User) -> None:
    client.force_login(admin_user)

    response = client.post(reverse("djdt:hijack_search"), {"q": "a"})

    assert response.status_code == 405


# Panel wiring


def test_url_resolves_in_djdt_namespace() -> None:
    url = reverse("djdt:hijack_search")
    match = resolve(url)

    assert url.endswith("/hijack/search/")
    assert match.view_name == "djdt:hijack_search"
    assert match.func is views.search_users
    assert match.kwargs == {"panel_class": HijackPanel}


def test_scripts_include_panel_js(make_panel: MakePanel, admin_user: User) -> None:
    panel = make_panel(admin_user)

    assert static("debug_toolbar_hijack/js/panel.js") in panel.scripts


def test_template_renders_combobox(make_panel: MakePanel, admin_user: User) -> None:
    User.objects.create_user("alice")

    panel = make_panel(admin_user)
    content = panel.content

    assert stats(panel)["search_url"] == reverse("djdt:hijack_search")
    assert 'role="combobox"' in content
    assert 'aria-autocomplete="list"' in content
    assert 'aria-expanded="false"' in content
    assert 'aria-controls="djdt-hijack-listbox"' in content
    assert '<ul id="djdt-hijack-listbox" role="listbox"' in content
    assert 'role="option"' in content
    assert '<span class="djdt-hijack-label">alice</span>' in content
    # One server-rendered option for alice, plus the empty search template.
    assert '<template class="djdt-hijack-option-template">' in content
    assert 'name="user_pk" value=""' in content
    assert content.count('role="option"') == 2
    assert f'data-search-url="{reverse("djdt:hijack_search")}"' in content
    assert 'data-no-results-text="No matching users"' in content
    assert 'data-truncated-text="Showing the first 100 users."' in content


def test_no_combobox_without_users(make_panel: MakePanel, admin_user: User) -> None:
    content = make_panel(admin_user).content

    assert 'role="combobox"' not in content
