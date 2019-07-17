from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import HStoreField, ArrayField
from django.db import models

User = get_user_model()


def avatar_directory_path(instance, filename):
    return 'avatars/{0}/{1}'.format(instance.user.email, filename)


class IUserAccount(models.Model):
    GENDER_FEMALE = 'female'
    GENDER_MALE = 'male'
    GENDER_CHOICES = (
        (GENDER_FEMALE, GENDER_FEMALE),
        (GENDER_MALE, GENDER_MALE),
    )

    HEAR_ABOUT_US_GOOGLE = 'Google'
    HEAR_ABOUT_US_FACEBOOK = 'Google'
    HEAR_ABOUT_US_CHOICES = (
        (HEAR_ABOUT_US_GOOGLE, HEAR_ABOUT_US_GOOGLE),
        (HEAR_ABOUT_US_FACEBOOK, HEAR_ABOUT_US_FACEBOOK),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=100, blank=True, null=True, choices=GENDER_CHOICES)
    avatar = models.ImageField(blank=True, null=True, upload_to=avatar_directory_path)
    hearAboutUs = models.CharField(max_length=100, blank=True, null=True, choices=HEAR_ABOUT_US_CHOICES)
    birthday = models.DateField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def role(self):
        raise Exception('IUserAccount child class must implement this attribute')


class Address(models.Model):
    ADDRESS_TYPE_HOME = 'home'
    ADDRESS_TYPE_BILLING = 'billing'
    ADDRESS_TYPE_STUDIO = 'studio'
    ADDRESS_TYPE_CHOICES = (
        (ADDRESS_TYPE_HOME, ADDRESS_TYPE_HOME),
        (ADDRESS_TYPE_BILLING, ADDRESS_TYPE_BILLING),
        (ADDRESS_TYPE_STUDIO, ADDRESS_TYPE_STUDIO),
    )

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
    PHONE_TYPE_MAIN = 'main'
    PHONE_TYPE_MOBILE = 'mobile'
    PHONE_TYPE_CHOICES = (
        (PHONE_TYPE_MAIN, PHONE_TYPE_MAIN),
        (PHONE_TYPE_MOBILE, PHONE_TYPE_MOBILE),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    phone_type = models.CharField(max_length=100, choices=PHONE_TYPE_CHOICES)
    phone_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Parent(IUserAccount):

    @property
    def role(self):
        return 'Parent'


class Instructor(IUserAccount):
    SOCIAL_MEDIA_INSTAGRAM = 'instagram'
    SOCIAL_MEDIA_TWITTER = 'twitter'
    SOCIAL_MEDIA_FACEBOOK = 'facebook'
    SOCIAL_MEDIA_LINKEDIN = 'linkedin'
    SOCIAL_MEDIA_CHOICES = (
        (SOCIAL_MEDIA_INSTAGRAM, SOCIAL_MEDIA_INSTAGRAM),
        (SOCIAL_MEDIA_TWITTER, SOCIAL_MEDIA_TWITTER),
        (SOCIAL_MEDIA_FACEBOOK, SOCIAL_MEDIA_FACEBOOK),
        (SOCIAL_MEDIA_LINKEDIN, SOCIAL_MEDIA_LINKEDIN),
    )

    LANG_ENGLISH = 'english'
    LANG_SPANISH = 'spanish'
    LANG_CHOICES = (
        (LANG_ENGLISH, LANG_ENGLISH),
        (LANG_SPANISH, LANG_SPANISH),
    )

    bio = models.TextField(blank=True, null=True)
    bio_title = models.CharField(max_length=250, blank=True, null=True)
    bio_description = models.TextField(blank=True, null=True)
    social_media_accounts = HStoreField(blank=True, null=True)
    instruments = models.ManyToManyField('instruments.Instrument', through='accounts.InstructorInstruments')
    languages = ArrayField(base_field=models.CharField(max_length=100, blank=True, choices=LANG_CHOICES), blank=True,
                           null=True)
    music = models.TextField(blank=True, null=True)

    # --- Job preferences ---
    job_prefs_one_student = models.BooleanField(default=False)
    job_prefs_small_groups = models.BooleanField(default=False)
    job_prefs_large_groups = models.BooleanField(default=False)
    job_prefs_children = models.BooleanField(default=False)
    job_prefs_teens = models.BooleanField(default=False)
    job_prefs_adults = models.BooleanField(default=False)
    job_prefs_seniors = models.BooleanField(default=False)

    # --- Qualifications ---
    qualif_certified_teacher = models.BooleanField(default=False)
    qualif_music_therapy = models.BooleanField(default=False)
    qualif_music_production = models.BooleanField(default=False)
    qualif_ear_training = models.BooleanField(default=False)
    qualif_conducting = models.BooleanField(default=False)
    qualif_virtuoso_recognition = models.BooleanField(default=False)
    qualif_performance = models.BooleanField(default=False)
    qualif_music_theory = models.BooleanField(default=False)
    qualif_young_children_experience = models.BooleanField(default=False)
    qualif_repertoire_selection = models.BooleanField(default=False)

    # --- Place for lessons ---
    place_lessons_home = models.BooleanField(default=False)
    place_lessons_studio = models.BooleanField(default=False)
    place_lessons_online = models.BooleanField(default=False)

    # --- Rates ---
    rates_thirty_mins = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rates_forty_five_mins = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rates_sixty_mins = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rates_ninety_mins = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)


def __str__(self):
    return f'Instructor {self.user}'


@property
def role(self):
    return 'Instructor'


class Education(models.Model):
    DEGREE_TYPE_ASSOCIATE = 'associate'
    DEGREE_TYPE_BACHELORS = 'bachelors'
    DEGREE_TYPE_GRADUATE = 'graduate'
    DEGREE_TYPE_PROFESSIONAL = 'professional'
    DEGREE_TYPE_CERTIFICATION = 'certification'
    DEGREE_TYPE_OTHER = 'other'
    DEGREE_TYPE_CHOICES = (
        (DEGREE_TYPE_ASSOCIATE, 'Associate Degree'),
        (DEGREE_TYPE_BACHELORS, 'Bachelor\'s Degree'),
        (DEGREE_TYPE_GRADUATE, 'Graduate Degreee'),
        (DEGREE_TYPE_PROFESSIONAL, 'Professional Degree'),
        (DEGREE_TYPE_CERTIFICATION, 'Certification'),
        (DEGREE_TYPE_OTHER, 'Other'),
    )
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='education')
    school = models.CharField(max_length=200, blank=True, null=True)
    graduation_year = models.IntegerField(blank=True, null=True)
    degree_type = models.CharField(max_length=100, blank=True, null=True, choices=DEGREE_TYPE_CHOICES)
    field_of_study = models.CharField(max_length=100, blank=True, null=True)
    school_location = models.CharField(max_length=100, blank=True, null=True)


class Employment(models.Model):
    MONTH_JANUARY = 'january'
    MONTH_FEBRUARY = 'february'
    MONTH_MARCH = 'march'
    MONTH_APRIL = 'april'
    MONTH_MAY = 'may'
    MONTH_JUNE = 'june'
    MONTH_JULY = 'july'
    MONTH_AUGUST = 'august'
    MONTH_SEPTEMBER = 'september'
    MONTH_OCTOBER = 'october'
    MONTH_NOVEMBER = 'november'
    MONTH_DECEMBER = 'december'
    MONTH_CHOICES = (
        (MONTH_JANUARY, MONTH_JANUARY),
        (MONTH_FEBRUARY, MONTH_FEBRUARY),
        (MONTH_MARCH, MONTH_MARCH),
        (MONTH_APRIL, MONTH_APRIL),
        (MONTH_MAY, MONTH_MAY),
        (MONTH_JUNE, MONTH_JUNE),
        (MONTH_JULY, MONTH_JULY),
        (MONTH_AUGUST, MONTH_AUGUST),
        (MONTH_SEPTEMBER, MONTH_SEPTEMBER),
        (MONTH_OCTOBER, MONTH_OCTOBER),
        (MONTH_NOVEMBER, MONTH_NOVEMBER),
        (MONTH_DECEMBER, MONTH_DECEMBER),
    )

    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='employment')
    employer = models.CharField(max_length=100, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    job_location = models.CharField(max_length=100, blank=True, null=True)
    from_month = models.CharField(max_length=100, blank=True, null=True, choices=MONTH_CHOICES)
    from_year = models.IntegerField(blank=True, null=True)
    to_month = models.CharField(max_length=100, blank=True, null=True, choices=MONTH_CHOICES)
    to_year = models.IntegerField(blank=True, null=True)
    still_work_here = models.BooleanField(default=False)


class Availability(models.Model):
    DAY_MONDAY = 'monday'
    DAY_TUESDAY = 'tuesday'
    DAY_WEDNESDAY = 'wednesday'
    DAY_THURSDAY = 'thursday'
    DAY_FRIDAY = 'friday'
    DAY_SATURDAY = 'saturday'
    DAY_SUNDAY = 'sunday'
    DAY_CHOICES = (
        (DAY_SUNDAY, DAY_SUNDAY),
        (DAY_MONDAY, DAY_MONDAY),
        (DAY_TUESDAY, DAY_TUESDAY),
        (DAY_WEDNESDAY, DAY_WEDNESDAY),
        (DAY_THURSDAY, DAY_THURSDAY),
        (DAY_FRIDAY, DAY_FRIDAY),
        (DAY_SATURDAY, DAY_SATURDAY),
    )

    SCHEDULE_8_10 = '8AM-10AM'
    SCHEDULE_10_12 = '10AM-12PM'
    SCHEDULE_12_3 = '12PM-3PM'
    SCHEDULE_3_6 = '3PM-6PM'
    SCHEDULE_CHOICES = (
        (SCHEDULE_8_10, SCHEDULE_8_10),
        (SCHEDULE_10_12, SCHEDULE_10_12),
        (SCHEDULE_12_3, SCHEDULE_12_3),
        (SCHEDULE_3_6, SCHEDULE_3_6),
    )

    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    schedule = models.CharField(max_length=10, choices=SCHEDULE_CHOICES)


class InstructorInstruments(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.CASCADE)


class Student(IUserAccount):
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, blank=True, null=True, related_name='students')

    @property
    def role(self):
        return 'Student'
