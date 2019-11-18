from django.db import models


class Offer(models.Model):
    name = models.CharField(max_length=100)
    content = models.TextField()
    show_at = models.DateTimeField(blank=True, null=True)
    hide_at = models.DateTimeField(blank=True, null=True)
    displayed = models.BooleanField(blank=True, default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
