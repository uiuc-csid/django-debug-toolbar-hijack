# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-09

### Added

- Release mise tasks that work with the protected `main` branch. `mise run release:prepare <version|bump>` bumps the version, moves the `[Unreleased]` changelog entries under the new version, commits on a `release/vX` branch and opens a PR. After the PR is merged, `mise run release:tag` tags the merge and, with `--push`, pushes only the tag. The `Release` workflow now fails if the tag doesn't match the `pyproject.toml` version.

## [0.1.0b1] - 2026-11-09

First beta release.

### Added

- `HijackPanel`, a django-debug-toolbar panel that lists hijackable users with one-click hijack buttons, shows the current hijack history, and offers a release button while impersonating.
- `HIJACK_USER_QUERYSET` setting: a dotted path or callable `(*, user) -> QuerySet` that picks the users the panel lists and searches.
- `debug_toolbar_hijack.users.superusers_only`, the default `HIJACK_USER_QUERYSET`. It mirrors django-hijack's `superusers_only` permission check but leaves out the current user.
- A `user_limit` cap on the list and search results (100 by default). The nav subtitle shows "100+ hijackable" and the panel notes that only the first users are shown when the cap is reached.
- A search combobox that finds users past the cap. It uses the user model's admin `search_fields` and `get_search_results()`, falls back to the username and email fields, and supports a custom `admin_site` on the panel.
- Type information (`py.typed`); the package passes mypy in strict mode.

### Fixed

- The panel no longer crashes when `HIJACK_USER_QUERYSET` is unset.
- The user list is sorted by the user model's `USERNAME_FIELD` instead of a hard-coded `username`, so custom user models work.

[Unreleased]: https://github.com/uiuc-csid/django-debug-toolbar-hijack/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/uiuc-csid/django-debug-toolbar-hijack/compare/v0.1.0b1...v0.1.0
[0.1.0b1]: https://github.com/uiuc-csid/django-debug-toolbar-hijack/releases/tag/v0.1.0b1
