from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(blank=True, default='', max_length=120)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
