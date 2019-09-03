from django.db import models
from django.contrib.auth.models import AbstractUser
from .constants import *


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(blank=True, default='', max_length=120)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def get_type(self):
        if hasattr(self, 'instructor'):
            return ROLE_INSTRUCTOR
        elif hasattr(self, 'parent'):
            return ROLE_PARENT
        else:
            return ROLE_STUDENT
