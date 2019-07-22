from django.contrib.auth import get_user_model
from django.db import models

from core.constants import SKILL_LEVEL_CHOICES, PLACE_FOR_LESSONS_CHOICES, LESSON_DURATION_CHOICES

User = get_user_model()


# TODO: classes Lesson, Application

class Instrument(models.Model):
    name = models.CharField(max_length=250)


class LessonRequest(models.Model):
    # user making the request, can be Parent or Student
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    message = models.TextField()
    instrument = models.ForeignKey(Instrument, on_delete=models.SET_NULL, blank=True, null=True)
    skill_level = models.CharField(max_length=100, blank=True, null=True, choices=SKILL_LEVEL_CHOICES)
    place_for_lessons = models.CharField(max_length=100, blank=True, null=True, choices=PLACE_FOR_LESSONS_CHOICES)
    lessons_duration = models.CharField(max_length=100, blank=True, null=True, choices=LESSON_DURATION_CHOICES)
    students = models.ManyToManyField('accounts.Student', through='lesson.LessonStudent')


class LessonStudent(models.Model):
    lesson = models.ForeignKey(LessonRequest, on_delete=models.CASCADE)
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE)
