from django.contrib.postgres.fields import JSONField
from django.db import models

from accounts.models import Instructor
from core.models import ProviderRequest, User


class BackgroundCheckRequest(models.Model):
    PRELIMINARY = 'preliminary'
    REQUESTED = 'requested'
    COMPLETE = 'complete'
    CANCELLED = 'cancelled'
    STATUSES = (
        (PRELIMINARY, PRELIMINARY),
        (REQUESTED, REQUESTED),
        (COMPLETE, COMPLETE),
        (CANCELLED, CANCELLED),
    )
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='bg_check_requests')
    instructor = models.ForeignKey(Instructor, null=True, on_delete=models.SET_NULL, related_name='bg_check_requests')
    status = models.CharField(max_length=100, choices=STATUSES, default=PRELIMINARY)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BackgroundCheckStep(models.Model):
    """Register steps made with Provider"""
    request = models.ForeignKey(BackgroundCheckRequest, on_delete=models.CASCADE, related_name='steps')
    step = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=200)   # id of resource, returned by provider
    data = JSONField(default=dict)   # relevant data returned by provider
    provider_request = models.ForeignKey(ProviderRequest, null=True, on_delete=models.SET_NULL)
    previous_step = models.ForeignKey('BackgroundCheckStep', null=True, on_delete=models.SET_NULL,
                                      related_name='next_step')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
