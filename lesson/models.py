import datetime as dt

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.utils import timezone

from accounts.models import Instructor, Parent, Student, TiedStudent
from core.constants import *
from core.models import ScheduledEmail
from payments.models import Payment

from lesson.utils import get_date_time_from_datetime_timezone, get_next_date_same_weekday

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
    tied_student = models.ForeignKey(TiedStudent, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=9, decimal_places=4)
    request = models.OneToOneField(LessonRequest, blank=True, null=True, on_delete=models.CASCADE,
                                   related_name='booking')
    application = models.ForeignKey(Application, blank=True, null=True, on_delete=models.CASCADE, related_name='bookings')
    instructor = models.ForeignKey(Instructor, blank=True, null=True, on_delete=models.SET_NULL, related_name='bookings')
    rate = models.DecimalField(max_digits=9, decimal_places=4, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=50, choices=STATUSES, default=REQUESTED)
    details = JSONField(blank=True, default=dict)
    payment = models.OneToOneField(Payment, blank=True, null=True, on_delete=models.SET_NULL,
                                   related_name='lesson_bookings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def remaining_lessons(self):
        """How many lessons remain to take/course from booking"""
        return self.quantity - self.lessons.filter(status=Lesson.COMPLETE).count()

    def get_request(self):
        if self.application:
            return self.application.request
        else:
            return self.request

    def student_details(self):
        """Return a list"""
        if self.user.is_parent():
            return {'name': self.tied_student.name, 'age': self.tied_student.age}
        else:
            return {'name': self.user.first_name, 'age': self.user.student.age}

    @classmethod
    def create_trial_lesson(cls, user, tied_student=None):
        """Create a LessonBooking for trial lesson, and related Lesson.
        Return created Lesson instance."""
        with transaction.atomic():
            lb = LessonBooking.objects.create(user=user, tied_student=tied_student,
                                              quantity=1, total_amount=0, description='Trial Lesson',
                                              status=LessonBooking.TRIAL)
            lesson = Lesson.objects.create(booking=lb)
        return lesson

    def create_lesson_request(self, lesson=None):
        """Create a LessonRequest instance from current LessonBooking. Return None if could not be possible"""
        instrument = skill_level = None
        if self.user.is_student():
            student_details = self.user.student_details.first()
            if student_details:
                instrument = student_details.instrument
                skill_level = student_details.skill_level
        elif self.user.is_parent():
            if self.tied_student and self.tied_student.tied_student_details:
                instrument = self.tied_student.tied_student_details.instrument
                skill_level = self.tied_student.tied_student_details.skill_level
        if instrument and skill_level:
            title = f'{instrument.name.capitalize()} Instructor'
            with transaction.atomic():
                if lesson:
                    request = LessonRequest.objects.create(user=self.user,
                                                           title=title,
                                                           instrument=instrument,
                                                           skill_level=skill_level,
                                                           place_for_lessons=PLACE_FOR_LESSONS_ONLINE,
                                                           lessons_duration=LESSON_DURATION_30,
                                                           trial_proposed_datetime=lesson.scheduled_datetime,
                                                           trial_proposed_timezone=lesson.scheduled_timezone,
                                                           )
                    lesson.booking.request = request
                    lesson.booking.save()
                else:
                    request = LessonRequest.objects.create(user=self.user,
                                                           title=title,
                                                           instrument=instrument,
                                                           skill_level=skill_level,
                                                           place_for_lessons=PLACE_FOR_LESSONS_ONLINE,
                                                           lessons_duration=LESSON_DURATION_30,
                                                           )
                if self.user.is_parent() and self.tied_student:
                    request.students.add(self.tied_student)
            return request
        else:
            return None

    def create_lessons(self, last_lesson):
        next_date = get_next_date_same_weekday(last_lesson.scheduled_datetime.date())
        next_datetime = dt.datetime.combine(next_date, last_lesson.scheduled_datetime.time(),
                                            tzinfo=last_lesson.scheduled_datetime.tzinfo)
        for i in range(self.quantity):
            lesson = Lesson.objects.create(booking=self,
                                           scheduled_datetime=next_datetime,
                                           scheduled_timezone=last_lesson.scheduled_timezone,
                                           instructor=self.instructor,
                                           rate=self.rate,
                                           status=Lesson.SCHEDULED)
            ScheduledEmail.objects.create(function_name='send_reminder_grade_lesson',
                                          schedule=lesson.scheduled_datetime + timezone.timedelta(minutes=30),
                                          parameters={'lesson_id': lesson.id})
            ScheduledEmail.objects.create(function_name='send_lesson_reminder',
                                          schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=60),
                                          parameters={'lesson_id': lesson.id, 'user_id': lesson.booking.user.id})
            if lesson.instructor:
                ScheduledEmail.objects.create(function_name='send_lesson_reminder',
                                              schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=60),
                                              parameters={'lesson_id': lesson.id, 'user_id': lesson.instructor.user.id})
            next_date = next_date + dt.timedelta(days=7)
            next_datetime = dt.datetime.combine(next_date, last_lesson.scheduled_datetime.time(),
                                                tzinfo=last_lesson.scheduled_datetime.tzinfo)


class Lesson(models.Model):
    PENDING = 'pending'
    SCHEDULED = 'scheduled'
    MISSED = 'missed'  # when datetime happens but lesson did not occurs
    COMPLETE = 'complete'   # when lesson was successful and graded
    STATUSES = (
        (SCHEDULED, SCHEDULED),
        (MISSED, MISSED),
        (COMPLETE, COMPLETE),
    )
    booking = models.ForeignKey(LessonBooking, on_delete=models.CASCADE, related_name='lessons')
    student_details = JSONField(blank=True, default=dict)   # data obtained from LessonRequest
    scheduled_datetime = models.DateTimeField(blank=True, null=True)
    scheduled_timezone = models.CharField(max_length=50, blank=True)
    # instructor and rate are copied from LessonBooking
    instructor = models.ForeignKey(Instructor, blank=True, null=True, on_delete=models.SET_NULL, related_name='lessons')
    rate = models.DecimalField(max_digits=9, decimal_places=4, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUSES, default=PENDING)
    grade = models.PositiveSmallIntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)   # added on grade
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    @classmethod
    def get_next_lesson(cls, user, tied_student=None):
        lessons = None
        if user.is_instructor():
            lessons = cls.objects.filter(booking__instructor=user.instructor, status=cls.SCHEDULED,
                                         scheduled_datetime__gt=timezone.now()).order_by('scheduled_datetime')
        elif tied_student:
            if cls.objects.filter(booking__isnull=False, booking__user=user,
                                  booking__tied_student__isnull=False, booking__tied_student=tied_student).count():
                lessons = cls.objects.filter(booking__user=user, status=cls.SCHEDULED, booking__tied_student=tied_student,
                                             scheduled_datetime__gt=timezone.now()).order_by('scheduled_datetime')
        elif cls.objects.filter(booking__isnull=False).filter(booking__user=user).count():
            lessons = cls.objects.filter(booking__user=user, status=cls.SCHEDULED,
                                         scheduled_datetime__gt=timezone.now()).order_by('scheduled_datetime')
        if lessons is not None:
            return lessons.first()
        else:
            return lessons

    @classmethod
    def get_last_lesson(cls, user, tied_student):
        if user.is_parent():
            return cls.objects.filter(booking__user=user, booking__tied_student=tied_student).last()
        else:
            return cls.objects.filter(booking__user=user).last()


class InstructorAcceptanceLessonRequest(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='acceptance_requests')
    request = models.ForeignKey(LessonRequest, on_delete=models.CASCADE, related_name='acceptances')
    accept = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('instructor', 'request')
