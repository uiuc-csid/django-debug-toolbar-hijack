# Plan: beta release prep for django-debug-toolbar-hijack

## Context

The package was just set up as a uv src-layout library (`django-debug-toolbar-hijack` on PyPI, imported as `debug_toolbar_hijack`). Nothing is committed yet, and it has no tests, linting, type checking, docs or CI. The panel also crashes if `settings.HIJACK_USER_QUERYSET` is unset. That setting belongs to this package, not to django-hijack, which only has `HIJACK_PERMISSION_CHECK` (default `hijack.permissions.superusers_only`). The goal is a `0.1.0b1` release that can be published, with tests, lint/format and type checks run through mise and hk, plus CI and a PyPI publish workflow.

Decisions already made: when the setting is unset, the fallback mirrors `superusers_only`; type checking uses mypy with django-stubs; release infrastructure is GitHub Actions CI plus PyPI trusted publishing.

## Open questions

Each item lists the default the plan uses unless the user says otherwise.

1. **License**: MIT, with a `LICENSE` file. *Needs user confirmation; PyPI metadata depends on it.*
2. **Fallback leaves out the current user**: `debug_toolbar_hijack.users.superusers_only` matches hijack's `superusers_only`, except that it doesn't list the current user. hijack itself allows a superuser to hijack themselves. This is a deliberate difference and will be documented.
3. **Showing a capped list**: when the list reaches `user_limit` (100), show "100+" in the nav subtitle and a "showing first N" note in the panel. The other option is to leave it as is and only document the cap.
4. **Where ruff and mypy come from**: they go in the uv `dev` group, not mise `[tools]`. mypy has to share an environment with django-stubs and the project's dependencies for the Django plugin to work, and keeping ruff in the same group keeps every version in `uv.lock`. mise only provides python, uv, hk and pkl.
5. **Lowest django-debug-toolbar version**: to be decided during implementation from debug-toolbar's changelog: the lowest version whose `Panel` API (`record_stats`, `get_stats`, `nav_subtitle` property) and Django/Python support fit `django>=5.2`, `python>=3.10`. `test:lowest` in CI then checks it.
6. **hk built-in step names**: check them with `hk builtins` against the pinned hk version before writing `hk.pkl`. If there is no mypy built-in, use a custom step.
7. **`USERNAME_FIELD` ordering**: the panel sorts by the user model's `USERNAME_FIELD` in place of the hard-coded `"username"`. This is a bug fix for custom user models, not an open choice, and is listed here so it is noticed.

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
  - Optional small fix: `nav_subtitle` reports the capped count. Either record `truncated: True` and show "100+", or leave it as is and document the cap.
- **`templates/.../panel.html`**: show a "showing first N" note when the list is truncated, if that option is taken.

## 2. Packaging — `pyproject.toml`

- Set `version = "0.1.0b1"`. Add a license (assume MIT; add a `LICENSE` file), `license-files`, `keywords`, `classifiers` (Framework :: Django :: 5.2 / 6.0, Python versions, Development Status :: 4 - Beta), and `[project.urls]`.
- Fix the dependency floors to deliberate minimums: `django>=5.2`, `django-debug-toolbar>=…`, `django-hijack>=3.7`. Check debug-toolbar's own Django and Python floors and pick the lowest version that actually supports the `Panel` API in use.
- Add `[dependency-groups] dev`: `pytest`, `pytest-django`, `pytest-cov`, `ruff`, `mypy`, `django-stubs[compatible-mypy]`.
- Add tool config in pyproject:
  - `[tool.ruff]`: target py310, line length 88, and a lint `select` of E, F, W, I, UP, B, SIM, DJ, RUF, PT.
  - `[tool.mypy]`: strict, `plugins = ["mypy_django_plugin.main"]`, and `[tool.django-stubs] django_settings_module = "tests.settings"`. Add `ignore_missing_imports` overrides for `debug_toolbar.*` and `hijack.*` if they ship untyped.
  - `[tool.pytest.ini_options]`: `DJANGO_SETTINGS_MODULE = "tests.settings"`, `pythonpath = ["."]`.
- Add a `CHANGELOG.md`. Delete `src.bkp/` once its contents are confirmed copied.

## 3. Tooling — mise + hk

- **`mise.toml`**
  - `[tools]`: `python` (3.13 dev default), `uv`, `hk`, `pkl` (hk's config is written in Pkl).
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
  - A custom `mypy` step with `check = "uv run mypy src tests"` and `glob = "**/*.py"`. The step runs on the whole project because the Django plugin needs the full project, not individual files.
  - Optional generic checks: trailing whitespace, end-of-file newline, `check_toml`/`check_yaml` builtins if present.
  - Hooks: `pre-commit` runs `fix = true` with ruff only, to stay fast. `check` runs everything, and CI uses it.
  - Confirm the builtin names against the installed hk version (`hk builtins`) during implementation.

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

## 5. Docs — `README.md`

- Sections: what the panel does (with a screenshot later), installation, setup (`INSTALLED_APPS`, `DEBUG_TOOLBAR_PANELS` entry, `path("hijack/", include("hijack.urls"))` required), and compatibility table.
- **Settings**:
  - `HIJACK_USER_QUERYSET`: a dotted path to a callable `(*, user) -> QuerySet` that receives the current (hijacking) user. Defaults to `debug_toolbar_hijack.users.superusers_only`. Include an example for `superusers_and_staff`.
  - Note that the list is display only: hijack's acquire view still enforces `HIJACK_PERMISSION_CHECK`, so keep the two in sync.
  - `user_limit`: change it by subclassing the panel.
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
4. `uv build`, then check the wheel contains the template and `py.typed`. Then `uvx twine check dist/*` for metadata and README rendering.
5. Manual smoke test: a throwaway `django-admin startproject` with the wheel installed. Confirm the panel lists users for a superuser, hijacks and then releases.
6. A commit triggers the hk pre-commit hook, and pushing a branch runs CI green on GitHub.
