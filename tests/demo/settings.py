"""Settings for a local demo site to try the panel by hand.

Run it with ``.venv/bin/python tests/demo/manage.py demo``. Every request is
logged in as the demo superuser, so never use this outside local development.
"""

from pathlib import Path

from tests.settings import *  # noqa: F403
from tests.settings import INSTALLED_APPS, MIDDLEWARE

DEBUG = True
ROOT_URLCONF = "tests.demo.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(Path(__file__).with_name("db.sqlite3")),
    }
}

INSTALLED_APPS = [*INSTALLED_APPS, "tests.demo"]

MIDDLEWARE = [*MIDDLEWARE]
MIDDLEWARE.insert(
    MIDDLEWARE.index("hijack.middleware.HijackUserMiddleware"),
    "tests.demo.middleware.auto_login",
)

DEBUG_TOOLBAR_CONFIG = {
    "IS_RUNNING_TESTS": False,
    "SHOW_TOOLBAR_CALLBACK": "tests.demo.middleware.show_toolbar",
}
