from django.contrib.auth import get_user_model
from django.db import models

from accounts.models import Instructor, Parent, Student, TiedStudent
from core.constants import (LESSON_DURATION_CHOICES, LR_NO_SEEN, LR_STATUSES, PLACE_FOR_LESSONS_CHOICES,
                            SKILL_LEVEL_CHOICES, )

from payments.models import Payment

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
    travel_distance = models.IntegerField(blank=True, null=True)

    students = models.ManyToManyField(TiedStudent)
    status = models.CharField(max_length=100, choices=LR_STATUSES, blank=True, default=LR_NO_SEEN)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def has_accepted_age(self, min_age=None, max_age=None):
        """Indicates if student related to LessonRequest has age in range [min_age, max_age]"""
        if min_age is None:
            min_age = -1
        if max_age is None:
            max_age = 200
        if self.user.is_parent():
            for item in self.students.all():
                if min_age <= item.age <= max_age:
                    return True
            return False
        else:
            return min_age <= self.user.student.age <= max_age


class Application(models.Model):
    request = models.ForeignKey(LessonRequest, related_name='applications', on_delete=models.PROTECT)
    instructor = models.ForeignKey(Instructor, related_name='applications', on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=9, decimal_places=4)
    message = models.TextField()
    status = models.CharField(max_length=100, choices=LR_STATUSES, default=LR_NO_SEEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LessonBooking(models.Model):
    REQUESTED = 'requested'
    PAID = 'paid'
    STATUSES = (
        (REQUESTED, REQUESTED),
        (PAID, PAID),
    )
    student = models.ForeignKey(Student, blank=True, null=True, on_delete=models.CASCADE,
                                related_name='lesson_bookings')
    parent = models.ForeignKey(Parent, blank=True, null=True, on_delete=models.CASCADE,
                               related_name='lesson_bookings')
    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=9, decimal_places=4)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='lesson_bookings')
    lesson_rate = models.DecimalField(max_digits=9, decimal_places=4)
    status = models.CharField(max_length=50, choices=STATUSES, default=REQUESTED)
    payment = models.ForeignKey(Payment, blank=True, null=True, on_delete=models.CASCADE,
                                related_name='lesson_bookings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
