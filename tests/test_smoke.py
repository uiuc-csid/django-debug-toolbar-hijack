from django.apps import apps

from debug_toolbar_hijack.panels import HijackPanel


def test_panel_imports() -> None:
    assert HijackPanel.template == "debug_toolbar_hijack/panel.html"


def test_app_is_installed() -> None:
    assert apps.is_installed("debug_toolbar_hijack")
