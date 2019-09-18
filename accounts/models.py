import uuid

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import HStoreField, ArrayField
from django.db import models

from core.constants import (
    ADDRESS_TYPE_CHOICES, BENEFIT_STATUSES, BENEFIT_TYPES, DAY_CHOICES, DEGREE_TYPE_CHOICES, GENDER_CHOICES,
    MONTH_CHOICES, PHONE_TYPE_CHOICES, SKILL_LEVEL_CHOICES,
)

User = get_user_model()


def avatar_directory_path(instance, filename):
    return 'avatars/{0}/{1}'.format(instance.user.email, filename)


class IUserAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=100, blank=True, null=True, choices=GENDER_CHOICES)
    avatar = models.ImageField(blank=True, null=True, upload_to=avatar_directory_path)
    birthday = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=150, default='')
    lat = models.CharField(max_length=50, default='')
    lng = models.CharField(max_length=50, default='')
    email_verified_at = models.DateTimeField(blank=True, null=True)
    referral_token = models.UUIDField(default=uuid.uuid4, blank=True, unique=True)
    referred_by = models.ForeignKey(User, blank=True, null=True, related_name='referral_%(class)ss',
                                    on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def role(self):
        raise Exception('IUserAccount child class must implement this attribute')


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=255, blank=True, null=True)
    address_type = models.CharField(max_length=100, choices=ADDRESS_TYPE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class PhoneNumber(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    number = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=100, choices=PHONE_TYPE_CHOICES)
    verified_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


def get_user_phone(user_acc):
    data = {}
    qs = PhoneNumber.objects.filter(user=user_acc.user)
    if qs.exists():
        phone = qs.all()[0]
        data = {'phone_number': phone.number,
                'is_verified': True if phone.verified_at is not None else False,
                }
    return data


class Parent(IUserAccount):
    # --- notifications ---
    application_received = models.BooleanField(default=False)
    lesson_taught_confirmed = models.BooleanField(default=False)
    payment_receipts = models.BooleanField(default=False)
    news_updates = models.BooleanField(default=False)
    offers = models.BooleanField(default=False)

    @property
    def role(self):
        return 'Parent'


class Instructor(IUserAccount):
    bio = models.TextField(blank=True, null=True)
    bio_title = models.CharField(max_length=250, blank=True, null=True)
    bio_description = models.TextField(blank=True, null=True)
    social_media_accounts = HStoreField(blank=True, null=True)
    instruments = models.ManyToManyField('lesson.Instrument', through='accounts.InstructorInstruments')
    languages = ArrayField(base_field=models.CharField(max_length=100, blank=True), blank=True, null=True)
    music = models.TextField(blank=True, null=True)

    job_preferences = ArrayField(blank=True, null=True, base_field=models.CharField(max_length=100))
    qualifications = ArrayField(blank=True, null=True, base_field=models.CharField(max_length=100))
    place_lessons_preferences = ArrayField(blank=True, null=True, base_field=models.CharField(max_length=100))
    rates = HStoreField(blank=True, null=True)

    # --- Notifications ---
    request_posted = models.BooleanField(default=False)
    student_booked_lesson = models.BooleanField(default=False)
    payment_receipts = models.BooleanField(default=False)
    news_updates = models.BooleanField(default=False)
    offers = models.BooleanField(default=False)

    disclosure_accepted_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'Instructor {self.user}'

    @property
    def role(self):
        return 'Instructor'


class Education(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='education')
    school = models.CharField(max_length=200, blank=True, null=True)
    graduation_year = models.IntegerField(blank=True, null=True)
    degree_type = models.CharField(max_length=100, blank=True, null=True, choices=DEGREE_TYPE_CHOICES)
    field_of_study = models.CharField(max_length=100, blank=True, null=True)
    school_location = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Employment(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='employment')
    employer = models.CharField(max_length=100, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    job_location = models.CharField(max_length=100, blank=True, null=True)
    from_month = models.CharField(max_length=100, blank=True, null=True, choices=MONTH_CHOICES)
    from_year = models.IntegerField(blank=True, null=True)
    to_month = models.CharField(max_length=100, blank=True, null=True, choices=MONTH_CHOICES)
    to_year = models.IntegerField(blank=True, null=True)
    still_work_here = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Availability(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    from1 = models.CharField(max_length=10, default='')
    to = models.CharField(max_length=10, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class InstructorInstruments(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    instrument = models.ForeignKey('lesson.Instrument', on_delete=models.CASCADE)
    skill_level = models.CharField(max_length=100, blank=True, null=True, choices=SKILL_LEVEL_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class InstructorLessonSize(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    one_student = models.BooleanField()
    small_groups = models.BooleanField()
    large_groups = models.BooleanField()


class InstructorAgeGroup(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    children = models.BooleanField()
    teens = models.BooleanField()
    adults = models.BooleanField()
    seniors = models.BooleanField()


class InstructorLessonRate(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    mins30 = models.FloatField()
    mins45 = models.FloatField()
    mins60 = models.FloatField()
    mins90 = models.FloatField()


class InstructorPlaceForLessons(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    home = models.BooleanField()
    studio = models.BooleanField()
    online = models.BooleanField()


class InstructorAdditionalQualifications(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    certified_teacher = models.BooleanField()
    music_therapy = models.BooleanField()
    music_production = models.BooleanField()
    ear_training = models.BooleanField()
    conducting = models.BooleanField()
    virtuoso_recognition = models.BooleanField()
    performance = models.BooleanField()
    music_theory = models.BooleanField()
    young_children_experience = models.BooleanField()
    repertoire_selection = models.BooleanField()


class Student(IUserAccount):
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, blank=True, null=True, related_name='students')

    @property
    def role(self):
        return 'Student'


class AccountBenefits(models.Model):
    benefit_type = models.CharField(max_length=50, choices=BENEFIT_TYPES)
    user_origin = models.ForeignKey(User, related_name='ref_%(class)s_benefits', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, choices=BENEFIT_STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class InstructorBenefits(AccountBenefits):
    instructor = models.ForeignKey(Instructor, related_name='benefits', on_delete=models.CASCADE)


class ParentBenefits(AccountBenefits):
    parent = models.ForeignKey(Parent, related_name='benefits',  on_delete=models.CASCADE)


class StudentBenefits(AccountBenefits):
    student = models.ForeignKey(Student, related_name='benefits',  on_delete=models.CASCADE)


def get_user_from_refer_code(ref_code):
    """Get an user from his refer_code"""
    user = None
    try:
        account = Instructor.objects.get(referral_token=ref_code)
    except models.ObjectDoesNotExist:
        account = None
    if account is None:
        try:
            account = Parent.objects.get(referral_token=ref_code)
        except models.ObjectDoesNotExist:
            account = None
    if account is None:
        try:
            account = Student.objects.get(referral_token=ref_code)
        except models.ObjectDoesNotExist:
            account = None
    if account is not None:
        user = account.user
    return user
