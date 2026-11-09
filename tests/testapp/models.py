"""Models used only by the test suite."""

from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class EmailUser(AbstractBaseUser):
    """A user model keyed on email, with no ``username`` field."""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = "email"

    objects = BaseUserManager["EmailUser"]()

    def __str__(self) -> str:
        return self.email
