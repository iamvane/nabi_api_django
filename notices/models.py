from django.db import models
from django.utils import timezone


class Offer(models.Model):
    name = models.CharField(max_length=100)
    content = models.TextField()
    percent_discount = models.IntegerField(blank=True, null=True)
    free_lesson = models.BooleanField(default=False)
    show_at = models.DateTimeField(blank=True, null=True)
    hide_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_last_active_offer(cls):
        today = timezone.now()
        return cls.objects.filter(show_at__lte=today).exclude(hide_at__lte=today).last()
