from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ReferenceRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reference_requests')
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
