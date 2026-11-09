# django-debug-toolbar-hijack

A [django-debug-toolbar](https://github.com/django-commons/django-debug-toolbar) panel for impersonating users with [django-hijack](https://github.com/django-hijack/django-hijack).

The **Hijack** panel lets you switch to another account straight from the debug toolbar:

- It lists the users you may hijack, each with a one-click **Hijack** button. The list is capped (100 users by default), and the nav subtitle shows how many users are available, for example "12 hijackable" or "100+ hijackable".
- A search box finds users past that cap. It searches the same way the user model's Django admin does.
- While you're impersonating someone, it shows who you're working as, the hijack history, and a **Release hijack** button.

The buttons POST to django-hijack's own acquire and release views, so hijack's permission checks, signals and session handling all still apply.

<!-- TODO: add a screenshot of the panel. -->

## Installation

```bash
pip install django-debug-toolbar-hijack
```

Or with uv:

```bash
uv add django-debug-toolbar-hijack
```

This installs Django, django-debug-toolbar and django-hijack if they aren't already installed.

## Setup

First set up [django-debug-toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/installation.html) and [django-hijack](https://django-hijack.readthedocs.io/en/stable/) as their docs describe. Then:

1. Add the app to `INSTALLED_APPS`, after `debug_toolbar` and `hijack`:

   ```python
   INSTALLED_APPS = [
       # ...
       "debug_toolbar",
       "hijack",
       "debug_toolbar_hijack",
   ]
   ```

2. Add the panel to `DEBUG_TOOLBAR_PANELS`. Setting `DEBUG_TOOLBAR_PANELS` replaces the toolbar's default panel list, so start from the defaults:

   ```python
   from debug_toolbar.settings import PANELS_DEFAULTS

   DEBUG_TOOLBAR_PANELS = [
       *PANELS_DEFAULTS,
       "debug_toolbar_hijack.panels.HijackPanel",
   ]
   ```

3. Include hijack's URLs. This is required: the panel's forms POST to `hijack:acquire` and `hijack:release`. The debug toolbar's URLs must be included too, since the search endpoint is served under them:

   ```python
   from debug_toolbar.toolbar import debug_toolbar_urls
   from django.urls import include, path

   urlpatterns = [
       # ...
       path("hijack/", include("hijack.urls")),
       *debug_toolbar_urls(),
   ]
   ```

django-hijack also needs `hijack.middleware.HijackUserMiddleware` in `MIDDLEWARE`; see its docs.

## Compatibility

| Package              | Supported versions                                 |
| -------------------- | -------------------------------------------------- |
| Python               | 3.10, 3.11, 3.12, 3.13, 3.14                       |
| Django               | 5.2 (Python 3.10+), 6.0 (Python 3.12+)             |
| django-debug-toolbar | 5.1.0 or later                                     |
| django-hijack        | 3.7 or later                                       |

CI tests every supported Python and Django combination, plus a run against the lowest allowed versions of each dependency.

## Settings

### `HIJACK_USER_QUERYSET`

Which users the panel lists and searches. It is a dotted path to a callable, or the callable itself, with this signature:

```python
def my_queryset(*, user: AbstractBaseUser | AnonymousUser) -> QuerySet: ...
```

`user` is the current (hijacking) user. The panel sorts the result by the user model's `USERNAME_FIELD`, so the callable doesn't need to order it.

The default is `debug_toolbar_hijack.users.superusers_only`. It mirrors django-hijack's default permission check, `hijack.permissions.superusers_only`: an active superuser sees every other active user, and everyone else sees nobody. Unlike hijack's check, it leaves out the current user, since hijacking yourself is never useful from a list.

If you use hijack's `superusers_and_staff` permission check, a matching queryset looks like this:

```python
# myproject/hijack.py
from django.contrib.auth import get_user_model


def superusers_and_staff(*, user):
    """Superusers see every other active user; staff see active non-staff users."""
    User = get_user_model()
    if not user.is_active:
        return User.objects.none()
    users = User.objects.filter(is_active=True).exclude(pk=user.pk)
    if user.is_superuser:
        return users
    if user.is_staff:
        return users.filter(is_staff=False, is_superuser=False)
    return User.objects.none()
```

```python
# settings.py
HIJACK_PERMISSION_CHECK = "hijack.permissions.superusers_and_staff"
HIJACK_USER_QUERYSET = "myproject.hijack.superusers_and_staff"
```

The list is display only. Clicking **Hijack** POSTs to hijack's acquire view, which still enforces `HIJACK_PERMISSION_CHECK`. If the queryset shows users that the permission check rejects, those buttons fail; if it leaves out users the check allows, you can't reach them from the panel. Keep the two settings in sync.

### Search

The search box queries a JSON endpoint that the panel adds under the debug toolbar's URLs. It returns 404 whenever the toolbar is hidden (`SHOW_TOOLBAR_CALLBACK`), and no results for anonymous users. Results always come from `HIJACK_USER_QUERYSET`, so search never shows a user the list wouldn't, and they're capped at the same `user_limit`.

Matching works like the Django admin's user changelist:

- When `django.contrib.admin` is installed and the user model is registered on the admin site with `search_fields`, the search calls that `ModelAdmin`'s `get_search_results()`. The `^`, `=` and `@` prefixes on `search_fields`, `get_search_fields()` overrides and custom `get_search_results()` overrides all apply.
- Otherwise, it does a case-insensitive substring match on the user model's `USERNAME_FIELD` and its email field, if it has one.

The admin site defaults to `django.contrib.admin.site`. If your user admin is registered on a custom `AdminSite`, set the panel's `admin_site` as shown below.

### Customizing the panel

`user_limit` and `admin_site` are attributes on the panel class. Change them by subclassing it and listing your subclass in `DEBUG_TOOLBAR_PANELS` instead of `HijackPanel`:

```python
# myproject/panels.py
from debug_toolbar_hijack.panels import HijackPanel


class MyHijackPanel(HijackPanel):
    # The most users to list and to return from a search (default 100).
    user_limit = 25
    # A dotted path to the AdminSite whose user ModelAdmin drives the search,
    # or the AdminSite itself (default "django.contrib.admin.site").
    admin_site = "myproject.admin.site"
```

```python
# settings.py
DEBUG_TOOLBAR_PANELS = [
    *PANELS_DEFAULTS,
    "myproject.panels.MyHijackPanel",
]
```

## Development

Tools and Python are managed with [mise](https://mise.jdx.dev/), the environment with [uv](https://docs.astral.sh/uv/), and checks with [hk](https://hk.jdx.dev/). mise syncs `.venv` with `uv sync` whenever `pyproject.toml` or `uv.lock` change.

```bash
mise install
```

```bash
mise run ci
```

`mise run ci` runs the `lint`, `typecheck` and `test` tasks. The others are:

| Task                       | What it does                                                                                               |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `mise run lint`            | Every hk check: ruff, ruff format, mypy, whitespace, Markdown                                              |
| `mise run fix`             | Every hk fixer                                                                                             |
| `mise run typecheck`       | mypy in strict mode with django-stubs                                                                      |
| `mise run test`            | pytest with coverage                                                                                       |
| `mise run test:lowest`     | pytest against the lowest allowed versions of the direct dependencies                                      |
| `mise run build`           | Build the sdist and wheel into `dist/`                                                                     |
| `mise run release:prepare` | Bump the version and update the changelog on a branch, then open a release PR; see [Releasing](#releasing) |
| `mise run release:tag`     | Tag the merged release and optionally push the tag; see [Releasing](#releasing)                            |

### Demo server

`tests/demo` is a small site for trying the panel by hand. It migrates a local SQLite database, seeds a superuser plus 151 other users (more than the default cap, so search has something to find), and starts the development server:

```bash
.venv/bin/python tests/demo/manage.py demo
```

Every request is logged in as the demo superuser, so never run it anywhere but your own machine. Claude Code users can also start it from `.claude/launch.json` as `hijack-demo`.

## Releasing

Releases publish to PyPI from GitHub Actions with [trusted publishing](https://docs.pypi.org/trusted-publishers/), so no API token is stored in GitHub.

One-time setup, before the first release:

1. On PyPI, add a GitHub trusted publisher (under [your account's publishing settings](https://pypi.org/manage/account/publishing/) before the project exists, or the project's **Settings → Publishing** after) with project name `django-debug-toolbar-hijack`, this repository's owner and name, workflow `release.yml`, and environment `pypi`.
2. On GitHub, create an environment named `pypi` under **Settings → Environments**. Optionally add required reviewers and restrict it to `v*` tags.

`main` is protected: changes land only through pull requests that pass CI. So a release takes two steps, a release PR and then a tag.

**1. Open the release PR.** From an up-to-date, clean `main` with the changes listed under `[Unreleased]` in `CHANGELOG.md`:

```bash
mise run release:prepare --dry-run beta
```

```bash
mise run release:prepare beta
```

The argument is an explicit version (such as `0.1.0b2`) or a [`uv version --bump`](https://docs.astral.sh/uv/reference/cli/#uv-version) keyword: `major`, `minor`, `patch`, `stable`, `alpha`, `beta`, `rc`, `post` or `dev`. The task:

1. Refuses to run unless the working tree is clean, the branch is `main` and it matches `origin/main`, the new version is newer than the current one, and neither the tag `vX` nor the branch `release/vX` exists locally or on `origin`.
2. Builds the new `CHANGELOG.md`: the `[Unreleased]` entries move under a dated heading for the new version and the compare links are updated. It refuses if `[Unreleased]` is empty, unless the new version is a pre-release that follows a pre-release of the same version (such as `0.1.0b1` → `0.1.0b2`); that release is noted as having no changes.
3. Runs `mise run ci`.
4. Creates the branch `release/vX` from `main`, bumps the version in `pyproject.toml` and `uv.lock` with `uv version`, writes the changelog and commits `Release vX`.
5. Pushes the branch and opens a PR to `main` with `gh pr create`. The PR body is the new changelog section and the next step.

`--no-pr` stops after the local commit and prints the push and `gh pr create` commands. `--dry-run` runs the checks, then shows every other step, the new version, the `CHANGELOG.md` diff and the PR body without changing anything. All checks run before anything is modified. The task never pushes to `main` and never creates a tag.

**2. Tag the release.** Once the PR is merged, update `main` and tag it:

```bash
git switch main && git pull --ff-only
```

```bash
mise run release:tag --dry-run
```

```bash
mise run release:tag --push
```

The task refuses to run unless the working tree is clean and `main` matches `origin/main`. It reads the version with `uv version --short`, checks that `CHANGELOG.md` has a section for it and that the tag `vX` doesn't exist locally or on `origin`, then creates the annotated tag `vX`.

The tag goes on the commit that set the version on `main` (the merge of the release PR), not necessarily `HEAD`. If other PRs were merged after the release PR, the task warns and lists them: they aren't part of the release, so the published package matches what the release PR and its changelog describe.

Without `--push`, the task prints the push command instead of running it. `--push` pushes only the tag (`git push origin refs/tags/vX`), which starts the `Release` workflow: it checks that the tag matches the `pyproject.toml` version, then builds the sdist and wheel and publishes them to PyPI.

## License

BSD-3-Clause. See [LICENSE](https://github.com/uiuc-csid/django-debug-toolbar-hijack/blob/main/LICENSE).
