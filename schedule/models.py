from django.db import models
from django.contrib.postgres.fields import JSONField

from core.utils import DayChoices


class InstructorRegularAvailability(models.Model):
    instructor = models.ForeignKey('accounts.Instructor', on_delete=models.CASCADE, related_name='regular_availability')
    week_day = models.IntegerField(choices=DayChoices.choices)
    schedule = JSONField()


class InstructorParticularAvailability(models.Model):
    instructor = models.ForeignKey('accounts.Instructor', on_delete=models.CASCADE,
                                   related_name='particular_availability')
    date = models.DateField()
    schedule = JSONField()
