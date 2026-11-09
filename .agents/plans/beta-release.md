# Plan: beta release prep for django-debug-toolbar-hijack

## Context

The package was just set up as a uv src-layout library (`django-debug-toolbar-hijack` on PyPI, imported as `debug_toolbar_hijack`). Nothing is committed yet, and it has no tests, linting, type checking, docs or CI. The panel also crashes if `settings.HIJACK_USER_QUERYSET` is unset. That setting belongs to this package, not to django-hijack, which only has `HIJACK_PERMISSION_CHECK` (default `hijack.permissions.superusers_only`). The goal is a `0.1.0b1` release that can be published, with tests, lint/format and type checks run through mise and hk, plus CI and a PyPI publish workflow.

Decisions already made: when the setting is unset, the fallback mirrors `superusers_only`; type checking uses mypy with django-stubs; release infrastructure is GitHub Actions CI plus PyPI trusted publishing.

## Resolved questions

1. **License**: BSD-3-Clause, the same license as Django, django-debug-toolbar and django-hijack. Add a `LICENSE` file and `license = "BSD-3-Clause"`.
2. **Fallback leaves out the current user**: confirmed. `debug_toolbar_hijack.users.superusers_only` matches hijack's `superusers_only`, except that it doesn't list the current user. Document this difference.
3. **Showing a capped list**: when the list reaches `user_limit` (100), the nav subtitle shows "100+" and the panel shows a "showing first N" note.
4. **Where ruff and mypy come from**: both go in the uv `dev` group. Remove `ruff` from mise `[tools]`. mise provides python, uv, hk, pkl and markdownlint-cli2.
5. **Lowest django-debug-toolbar version**: `django-debug-toolbar>=5.1.0`. It is the first release that lists Django 5.2 support (`requires-python >=3.9`), and the `Panel` API this package uses (`record_stats`, `get_stats`, `nav_subtitle` property) is older than that. `test:lowest` in CI confirms it.
6. **hk built-in step names** (checked against hk 2.11.1): `ruff`, `ruff_format`, `mypy`, `newlines`, `trailing_whitespace`, `markdown_lint`, `pkl`, `pkl_format` and `yamllint` exist. There is no TOML-check builtin. Use `Builtins.mypy` and change its `check` to run the whole project.
7. **`USERNAME_FIELD` ordering**: a bug fix, not a choice. The panel sorts by the user model's `USERNAME_FIELD` instead of the hard-coded `"username"`.

## 1. Code changes — `src/debug_toolbar_hijack/`

- **New `users.py`** with a public default the user can also reference in settings:
  
  ```python
  def superusers_only(*, user):
      """Mirror hijack.permissions.superusers_only as a queryset."""
      User = get_user_model()
      if not (user.is_active and user.is_superuser):   # hijacker must be superuser
          return User.objects.none()
      return User.objects.filter(is_active=True).exclude(pk=user.pk)
  ```

  hijack's own check does not stop a superuser from hijacking themselves. Excluding self is still the useful behavior for a list, and the docs will say so.
- **`panels.py`**
  - Resolve the queryset factory with `getattr(settings, "HIJACK_USER_QUERYSET", None)`. Accept a dotted path or a callable, and fall back to `users.superusers_only`.
  - Replace the hard-coded `.order_by("username")` with `get_user_model().USERNAME_FIELD`, because the current code breaks on custom user models.
  - Add type annotations so the package passes mypy in strict mode. `py.typed` already exists.
  - `nav_subtitle` reports the capped count: fetch `user_limit + 1` rows, record `truncated: True` when there are more than `user_limit`, and show "100+".
- **`templates/.../panel.html`**: show a "showing first N" note when the list is truncated.

## 1a. User search combobox

The panel lists at most `user_limit` users. A search box lets you find any user the hijack queryset allows, using the same search the user model's admin uses.

- **Search endpoint**: `HijackPanel.get_urls()` returns `path("hijack/search/", views.search_users, name="hijack_search")`. django-debug-toolbar mounts it under its `djdt` namespace, so the panel reverses `djdt:hijack_search`. The view:
  - is wrapped in debug-toolbar's `require_show_toolbar`, so it returns 404 wherever the toolbar is hidden;
  - returns an empty list for anonymous users;
  - starts from the same `HIJACK_USER_QUERYSET` factory as the panel, so search never shows more than the list allows;
  - reads `GET ?q=` and returns JSON `{"users": [{"pk", "label"}], "truncated": bool}`, sorted by `USERNAME_FIELD` and capped at `user_limit`.
- **Admin search fields** (`debug_toolbar_hijack/search.py`):
  - When `django.contrib.admin` is installed and the user model is registered (`admin_site.is_registered(User)`), get its `ModelAdmin` with `admin_site.get_model_admin(User)`. That method needs Django 5.0+, which the `django>=5.2` floor covers.
  - Call `model_admin.get_search_results(request, queryset, q)`. This uses `get_search_fields()`, including the `^`, `=` and `@` prefixes and any custom override. If it reports possible duplicates, apply `.distinct()`.
  - Fallback, when admin isn't installed, the model isn't registered, or `get_search_fields()` is empty: search `USERNAME_FIELD__icontains`, plus the `get_email_field_name()` field if the model has one.
  - The admin site defaults to `django.contrib.admin.site`. Projects with a custom `AdminSite` set the panel attribute `admin_site`, a dotted path, by subclassing the panel, the same way as `user_limit`.
- **Combobox UI** (`panel.html` + `static/debug_toolbar_hijack/js/panel.js`):
  - Add an `<input type="search" role="combobox" aria-autocomplete="list" aria-expanded aria-controls>` above the user list. The list is the `listbox`, and the search URL comes from a `data-search-url` attribute.
  - The toolbar inserts panel HTML with `innerHTML`, so inline scripts don't run. Load the JS through the panel's `scripts` property and bind it on the `djdt.panel.render` event.
  - Debounce input (~250 ms) and fetch with `credentials: "same-origin"`. Replace the list's acquire forms with the results, and restore the server-rendered list when the query is cleared. Arrow keys move through the results, Enter hijacks the active user and Escape clears the search. Show "No matching users" and the "showing first N" note when they apply.
  - Keep it dependency-free, vanilla JS only, and style it with the toolbar's existing CSS variables.
- Add `src/debug_toolbar_hijack/static/` to the wheel and check that it ships in the build verification step.

## 2. Packaging — `pyproject.toml`

- Set `version = "0.1.0b1"`. Add the BSD-3-Clause license (with a `LICENSE` file), `license-files`, `keywords`, `classifiers` (Framework :: Django :: 5.2 / 6.0, Python versions, Development Status :: 4 - Beta), and `[project.urls]`.
- Fix the dependency floors to deliberate minimums: `django>=5.2`, `django-debug-toolbar>=5.1.0`, `django-hijack>=3.7`.
- Add `[dependency-groups] dev`: `pytest`, `pytest-django`, `pytest-cov`, `ruff`, `mypy`, `django-stubs[compatible-mypy]`.
- Add tool config in pyproject:
  - `[tool.ruff]`: target py310, line length 88, and a lint `select` of E, F, W, I, UP, B, SIM, DJ, RUF, PT.
  - `[tool.mypy]`: strict, `plugins = ["mypy_django_plugin.main"]`, and `[tool.django-stubs] django_settings_module = "tests.settings"`. Add `ignore_missing_imports` overrides for `debug_toolbar.*` and `hijack.*` if they ship untyped.
  - `[tool.pytest.ini_options]`: `DJANGO_SETTINGS_MODULE = "tests.settings"`, `pythonpath = ["."]`.
- Add a `CHANGELOG.md`. Delete `src.bkp/` once its contents are confirmed copied.

## 3. Tooling — mise + hk

- **`mise.toml`**
  - `[tools]`: `uv`, `hk`, `pkl` (hk's config is written in Pkl) and `markdownlint-cli2`. Python comes from `.python-version`. Remove `ruff`, which moves to the uv `dev` group.
  - `[env]`: `_.python.venv = { path = ".venv", create = false }`.
  - `[hooks] postinstall = "hk install --mise"`.
  - Tasks:
    - `install` → `uv sync`
    - `lint` → `hk check --all`
    - `fix` → `hk fix --all`
    - `typecheck` → `uv run mypy src tests`
    - `test` → `uv run pytest --cov`
    - `test:lowest` → `uv run --resolution lowest-direct --isolated pytest`
    - `build` → `uv build`
    - `ci` → depends on lint, typecheck and test
- **`hk.pkl`**: amend hk's `Config.pkl` and import `Builtins.pkl`, pinned to the installed hk version. Steps:
  - `ruff` and `ruff_format` from builtins, overriding `check` and `fix` to `uv run ruff …` so they use the locked version.
  - `Builtins.mypy` with `check = "uv run mypy src tests"` and `glob = "**/*.py"`. The step runs on the whole project because the Django plugin needs the full project, not individual files.
  - Generic checks: `trailing_whitespace` and `newlines`, plus `yamllint` once workflows exist. There is no TOML-check builtin.
  - Hooks: `pre-commit` runs `fix = true` with ruff only, to stay fast. `check` runs everything, and CI uses it.

## 4. Tests — `tests/`

- `tests/settings.py`: SQLite in-memory database; apps `auth`, `contenttypes`, `sessions`, `debug_toolbar`, `hijack`, `debug_toolbar_hijack`; `DEBUG_TOOLBAR_PANELS` containing `debug_toolbar_hijack.panels.HijackPanel`; `DEBUG_TOOLBAR_CONFIG = {"IS_RUNNING_TESTS": False}` or the equivalent setting.
- `tests/urls.py`: include `hijack.urls` and the debug toolbar URLs.
- `tests/test_users.py`: tests for the default queryset:
  - A superuser gets the active users, without themselves or inactive users.
  - Staff, regular and anonymous users get none.
- `tests/test_panel.py` (build a `DebugToolbar(request, get_response)` with `RequestFactory` plus a session, call `panel.generate_stats`, then assert on `panel.get_stats()`):
  - The fallback is used when the setting is absent (`override_settings` / `del`).
  - A custom `HIJACK_USER_QUERYSET` dotted path is honored.
  - The `user_limit` cap applies.
  - Anonymous requests produce an empty list.
  - `hijack_history` is resolved to labels; a deleted user falls back to its pk.
  - The release URL and CSRF token are present, and the template renders (`panel.content`).
- `tests/test_integration.py`: log in as a superuser, POST to `hijack:acquire`, then render the panel and assert it shows `is_hijacked` with the right history.
- A custom user model test app (email as `USERNAME_FIELD`) to cover the ordering fix.
- `tests/test_search.py`:
  - Uses the registered `ModelAdmin`'s `search_fields`: register a test admin with `search_fields = ["email"]` and match on email.
  - Falls back to `USERNAME_FIELD` when the model isn't registered or has no search fields.
  - Results never include users outside `HIJACK_USER_QUERYSET`.
  - Anonymous users get an empty list.
  - Returns 404 when `SHOW_TOOLBAR_CALLBACK` is false.
  - The `user_limit` cap applies and sets `truncated`.
  - Honors a custom `admin_site`.
- A Playwright smoke test of the combobox is optional, not a beta blocker.

## 5. Docs — `README.md`

- Sections: what the panel does (with a screenshot later), installation, setup (`INSTALLED_APPS`, `DEBUG_TOOLBAR_PANELS` entry, `path("hijack/", include("hijack.urls"))` required), and compatibility table.
- **Settings**:
  - `HIJACK_USER_QUERYSET`: a dotted path to a callable `(*, user) -> QuerySet` that receives the current (hijacking) user. Defaults to `debug_toolbar_hijack.users.superusers_only`. Include an example for `superusers_and_staff`.
  - Note that the list is display only: hijack's acquire view still enforces `HIJACK_PERMISSION_CHECK`, so keep the two in sync.
  - `user_limit` and `admin_site`: change them by subclassing the panel.
- **Search**: the box uses the user model's admin `search_fields`, or `get_search_results` if overridden. Without one, it searches the username and email fields.
- Development section: `mise install`, then `mise run ci`.

## 6. CI / release — `.github/workflows/`

- **`ci.yml`** (push and PR): install tools with `jdx/mise-action`, then:
  - Job `lint`: `mise run lint` and `mise run typecheck`.
  - Job `test`: matrix of Python 3.10–3.14 × Django 5.2 / 6.0, excluding Django 6.0 on Python < 3.12. Run `uv run --with "django~=X.Y" pytest`, plus one `test:lowest` job.
- **`release.yml`** (on tag `v*`): `uv build`, then `uv publish` with PyPI trusted publishing (`id-token: write`, `environment: pypi`). Before running it, set up the trusted publisher on PyPI by hand; list that in the release steps.

## Verification

1. `mise install && mise run install`: tools and environment set up, hk hooks installed.
2. `mise run ci`: ruff, ruff format, mypy (strict) and pytest all pass, with coverage reported.
3. `mise run test:lowest`: passes on the minimum dependency versions.
4. `uv build`, then check the wheel contains the template, `static/` JS and `py.typed`. Then `uvx twine check dist/*` for metadata and README rendering.
5. Manual smoke test: a throwaway `django-admin startproject` with the wheel installed. Confirm the panel lists users for a superuser, the search box finds a user past the cap through the admin `search_fields`, and the panel hijacks and then releases.
6. A commit triggers the hk pre-commit hook, and pushing a branch runs CI green on GitHub.
