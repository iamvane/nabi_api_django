from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models

from accounts.models import Instructor, Parent, Student, TiedStudent
from core.constants import *
from payments.models import Payment

User = get_user_model()


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
    message = models.TextField(blank=True, default='')
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT)
    skill_level = models.CharField(max_length=100, choices=SKILL_LEVEL_CHOICES)
    place_for_lessons = models.CharField(max_length=100, choices=PLACE_FOR_LESSONS_CHOICES)
    lessons_duration = models.CharField(max_length=100, choices=LESSON_DURATION_CHOICES)
    travel_distance = models.IntegerField(blank=True, null=True)
    trial_proposed_datetime = models.DateTimeField(blank=True, null=True)
    trial_proposed_timezone = models.CharField(max_length=50, blank=True)
    students = models.ManyToManyField(TiedStudent, blank=True)
    status = models.CharField(max_length=100, choices=LESSON_REQUEST_STATUSES,
                              blank=True, default=LESSON_REQUEST_ACTIVE)

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
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LessonBooking(models.Model):
    REQUESTED = 'requested'
    PAID = 'paid'
    TRIAL = 'trial'
    CANCELLED = 'cancelled'
    STATUSES = (
        (REQUESTED, REQUESTED),
        (PAID, PAID),
        (TRIAL, TRIAL),
        (CANCELLED, CANCELLED),
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='lesson_bookings')
    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=9, decimal_places=4)
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='booking')
    description = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=50, choices=STATUSES, default=REQUESTED)
    details = JSONField(blank=True, default=dict)
    payment = models.OneToOneField(Payment, blank=True, null=True, on_delete=models.SET_NULL,
                                   related_name='lesson_bookings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def remaining_lessons(self):
        """How many lessons remain from booking"""
        return self.quantity - self.lessons.filter(grade__isnull=False).count()


class Lesson(models.Model):
    SCHEDULED = 'scheduled'
    MISSED = 'missed'  # when datetime happens but lesson did not occurs
    COMPLETE = 'complete'   # when lesson was successful and graded
    STATUSES = (
        (SCHEDULED, SCHEDULED),
        (MISSED, MISSED),
        (COMPLETE, COMPLETE),
    )
    booking = models.ForeignKey(LessonBooking, on_delete=models.CASCADE, related_name='lessons')
    student_details = JSONField(default=dict)
    scheduled_datetime = models.DateTimeField(blank=True, null=True)
    scheduled_timezone = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=50, choices=STATUSES, default=SCHEDULED)
    grade = models.PositiveSmallIntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)   # added on grade
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
