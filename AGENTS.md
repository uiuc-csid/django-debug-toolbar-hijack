# AGENTS.md

Guidance for AI coding agents working in this repository. This file is the single source of truth for agent instructions; `CLAUDE.md` imports it and should only hold Claude Code–specific additions.

## Project

`django-debug-toolbar-hijack` is a small Django app that adds a [django-debug-toolbar](https://github.com/django-commons/django-debug-toolbar) panel for impersonating users via [django-hijack](https://github.com/django-hijack/django-hijack).

- `src/debug_toolbar_hijack/panels.py` — `HijackPanel`: lists users from `settings.HIJACK_USER_QUERYSET` (capped at `user_limit`), shows current `hijack_history`, and renders acquire/release forms.
- `src/debug_toolbar_hijack/templates/debug_toolbar_hijack/panel.html` — panel template; forms POST to `hijack:acquire` / `hijack:release` with a CSRF token and a `next` URL.
- `src/debug_toolbar_hijack/apps.py` — `AppConfig`.
- `src/debug_toolbar_hijack/py.typed` — the package ships type information.

## Tooling

- Tool and Python versions are managed by [mise](https://mise.jdx.dev/). Install or pin tools (including Python, uv, and hk) with `mise use` / `mise install` rather than system package managers or ad-hoc installs.
- Package/env management: [uv](https://docs.astral.sh/uv/) with the `uv_build` backend (`src/` layout). Use `uv add` / `uv sync` / `uv run`; don't edit `uv.lock` by hand.
- Python: `requires-python >= 3.10` (local dev pinned to 3.14 in `.python-version`, which mise reads; `mise.toml` also creates/activates `.venv`).
- Linting/formatting: ruff (config in `pyproject.toml`), wired into hk via `hk.pkl`. Don't use syntax or stdlib features newer than 3.10.

## Conventions

- User-facing strings go through Django i18n (`gettext_lazy` in Python, `{% translate %}` / `{% blocktranslate %}` in templates).
- Keep the panel safe for large user tables and anonymous requests (see `user_limit` and the `is_authenticated` guard).
- Don't hard-wrap Markdown: write each paragraph or list item on a single line.
- Prefer the hk and mise MCP servers (configured in `.mcp.json`) over shelling out to `hk` or `mise` when they're available; fall back to the CLI only if MCP isn't.

## Plans

- Write implementation plans as Markdown files in `.agents/plans/`.
- When a plan is completed, move it to `.agents/archived-plans/`.
