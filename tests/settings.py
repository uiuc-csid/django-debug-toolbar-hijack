"""Minimal Django settings for the test suite."""

SECRET_KEY = "tests-only-not-secret"
DEBUG = True
USE_TZ = True
ROOT_URLCONF = "tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "debug_toolbar",
    "hijack",
    "debug_toolbar_hijack",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "hijack.middleware.HijackUserMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

INTERNAL_IPS = ["127.0.0.1"]

DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar_hijack.panels.HijackPanel",
]

DEBUG_TOOLBAR_CONFIG = {
    # The toolbar refuses to run under tests unless this is disabled.
    "IS_RUNNING_TESTS": False,
}
