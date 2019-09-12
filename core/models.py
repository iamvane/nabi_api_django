from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .constants import *


class UserManager(BaseUserManager):
    """Define required methods for custom User model usage."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Common operations when create an user."""
        if not email:
            raise ValueError('Email value is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_user(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField('email address', unique=True)
    username = models.CharField(blank=True, default='', max_length=120)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_role(self):
        if hasattr(self, 'instructor'):
            return ROLE_INSTRUCTOR
        elif hasattr(self, 'parent'):
            return ROLE_PARENT
        else:
            return ROLE_STUDENT
