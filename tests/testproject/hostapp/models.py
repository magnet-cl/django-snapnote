from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, handle, password=None, **extra):
        user = self.model(handle=handle, **extra)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, handle, password=None, **extra):
        return self.create_user(handle, password, is_staff=True, is_superuser=True, **extra)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """A user model with no email and a custom username field."""

    handle = models.CharField(max_length=50, unique=True)
    is_staff = models.BooleanField(default=False)
    USERNAME_FIELD = "handle"
    objects = CustomUserManager()
