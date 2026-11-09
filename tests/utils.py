from __future__ import annotations

from collections.abc import Callable
from typing import Any

from debug_toolbar_hijack.panels import HijackPanel

MakePanel = Callable[..., HijackPanel]


def stats(panel: HijackPanel) -> dict[str, Any]:
    """Return the panel's recorded stats (``get_stats`` is unannotated)."""
    result: dict[str, Any] = panel.get_stats()  # type: ignore[no-untyped-call]
    return result
