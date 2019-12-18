from django.contrib.auth import get_user_model
from django.db import models

from accounts.models import TiedStudent
from core.constants import (LESSON_DURATION_CHOICES, LR_NO_SEEN, LR_STATUSES, PLACE_FOR_LESSONS_CHOICES,
                            SKILL_LEVEL_CHOICES, )

User = get_user_model()


# TODO: classes Lesson, Application

class Instrument(models.Model):
    name = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class LessonRequest(models.Model):
    # user making the request, can be Parent or Student
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_requests')
    title = models.CharField(max_length=100)
    message = models.TextField()
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT)
    skill_level = models.CharField(max_length=100, choices=SKILL_LEVEL_CHOICES)
    place_for_lessons = models.CharField(max_length=100, choices=PLACE_FOR_LESSONS_CHOICES)
    lessons_duration = models.CharField(max_length=100, choices=LESSON_DURATION_CHOICES)
    students = models.ManyToManyField(TiedStudent)
    status = models.CharField(max_length=100, choices=LR_STATUSES, blank=True, default=LR_NO_SEEN)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
