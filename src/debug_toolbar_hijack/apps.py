from django.apps import AppConfig


class DebugToolbarHijackConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "debug_toolbar_hijack"
    verbose_name = "Debug Toolbar Hijack"
