from django.db import models

from core.utils import DayChoices


class InstructorRegularAvailability(models.Model):
    instructor = models.ForeignKey('accounts.Instructor', on_delete=models.CASCADE, related_name='regular_availability')
    week_day = models.IntegerField(choices=DayChoices.choices)
    begin_time = models.TimeField()
    end_time = models.TimeField()
    available = models.BooleanField()


class InstructorParticularAvailability(models.Model):
    instructor = models.ForeignKey('accounts.Instructor', on_delete=models.CASCADE,
                                   related_name='particular_availability')
    date = models.DateField()
    begin_time = models.TimeField()
    end_time = models.TimeField()
    available = models.BooleanField()
