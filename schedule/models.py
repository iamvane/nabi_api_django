from django.contrib.postgres.fields import JSONField
from django.db import models

from core.utils import DayChoices


class InstructorRegularAvailability(models.Model):
    instructor = models.ForeignKey('accounts.Instructor', on_delete=models.CASCADE, related_name='regular_availability')
    week_day = models.IntegerField(choices=DayChoices.choices)
    schedule = JSONField()

    class Meta:
        verbose_name_plural = 'Instructor Regular Availabilities'


class InstructorParticularAvailability(models.Model):
    instructor = models.ForeignKey('accounts.Instructor', on_delete=models.CASCADE,
                                   related_name='particular_availability')
    date = models.DateField()
    schedule = JSONField()

    class Meta:
        verbose_name_plural = 'Instructor Particular Availabilities'


def get_instructor_schedule(instructor, date):
    """Get schedule data for an instructor in a specific date"""
    if instructor.particular_availability.filter(date=date).exists():
        ins_ava = instructor.particular_availability.filter(date=date).first()
    else:
        week_day = date.weekday()
        ins_ava = instructor.regular_availability.filter(week_day=week_day).first()
    if ins_ava:
        return ins_ava.schedule
    else:
        return {}
