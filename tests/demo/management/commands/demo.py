"""Migrate, seed demo users, then start the development server."""

from __future__ import annotations

import os
from typing import Any

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser

from tests.demo.middleware import DEMO_USERNAME


class Command(BaseCommand):
    help = "Migrate, seed demo users and run the development server."

    def add_arguments(self, parser: CommandParser) -> None:
        # Claude's launch.json autoPort passes the assigned port in PORT.
        port = os.environ.get("PORT", "8765")
        parser.add_argument("addrport", nargs="?", default=f"127.0.0.1:{port}")

    def handle(self, *args: Any, **options: Any) -> None:
        call_command("migrate", verbosity=0)
        if not User.objects.filter(username=DEMO_USERNAME).exists():
            User.objects.create_superuser(DEMO_USERNAME, "admin@example.com", None)
            User.objects.bulk_create(
                User(
                    username=f"user{i:03}",
                    email=f"person{i:03}@example.org",
                    first_name="Name",
                    last_name=f"Last{i}",
                )
                for i in range(150)
            )
            User.objects.create_user(
                "zed", email="needle@haystack.test", last_name="Findme"
            )
            self.stdout.write("Seeded the demo users.")
        self.stdout.write(f"Open http://{options['addrport']}/")
        call_command("runserver", options["addrport"])
