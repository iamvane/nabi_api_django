import datetime
import re
from coolname import RandomGenerator
from coolname.loader import load_config
from os import path
from pygeocoder import Geocoder, GeocoderError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models import PointField
from django.contrib.postgres.fields import HStoreField, ArrayField
from django.db import models
from django.utils import timezone

from accounts.utils import add_to_email_list_v2

from core.constants import *
from core.utils import ElapsedTime, get_date_a_month_later, get_month_integer, send_admin_email

User = get_user_model()
coolname_config = load_config(path.join(settings.BASE_DIR, 'accounts', 'data'))
generator = RandomGenerator(coolname_config)


def avatar_directory_path(instance, filename):
    return 'avatars/{0}/{1}'.format(instance.user.email, filename)


class IUserAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)   # updated after save() method in User
    gender = models.CharField(max_length=100, blank=True, null=True, choices=GENDER_CHOICES)
    avatar = models.ImageField(blank=True, null=True, upload_to=avatar_directory_path)
    birthday = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=150, default='')
    coordinates = PointField(blank=True, null=True)
    lat = models.CharField(max_length=50, default='')
    lng = models.CharField(max_length=50, default='')
    email_verified_at = models.DateTimeField(blank=True, null=True)
    reference = models.CharField(max_length=200, blank=True)
    terms_accepted = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def role(self):
        raise Exception('IUserAccount child class must implement this attribute')

    @property
    def age(self):
        today = timezone.now()
        years = today.year - self.birthday.year
        if (today.month, today.day) < (self.birthday.month, self.birthday.day):
            years -= 1
        return years

    def get_location(self, result_type='string'):
        """ :param result_type: indicates how data should be returned
            :type result_type: 'string' (to return 'city, state' string), 'tuple' (to return country, state, city)
            If no result is obtained, return '' or ()."""
        if self.coordinates:
            try:
                lng = self.coordinates.coords[0]
                lat = self.coordinates.coords[1]
            except Exception as e:
                send_admin_email('[ALERT] Error getting coordinates',
                                 f"""Error with coordinates for user id {self.user.id}, email {self.user.email}. 
                                 Exception: {str(e)}"""
                                 )
                if result_type == 'string':
                    return ''
                else:
                    return ()
            try:
                geocoder = Geocoder(api_key=settings.GOOGLE_MAPS_API_KEY)
                locations = geocoder.reverse_geocode(lat, lng)
            except GeocoderError as e:
                locations = []
                send_admin_email('[ALERT] Empty location info',
                                 f"""When get location info from Google, an error occurs.
                                 User id {self.user.id}, email {self.user.email}, lat {lat}, long {lng}.
                                 Google API error: {str(e)}"""
                                 )
            city = state = ''
            if len(locations):
                country = locations[0].country__short_name
            for item in locations:
                if country == 'US':
                    state = item.state__short_name
                else:
                    state = item.state
                if item.city:
                    city = item.city
                    break
            if result_type == 'string':
                if state:
                    return '{}, {}'.format(city, state)
                else:
                    return ''
            else:
                if state:
                    return country, state, city
                else:
                    return ()
        else:
            if result_type == 'string':
                return ''
            else:
                return ()

    def set_display_name(self):
        """Change display_name value, only if different value is generated"""
        if self.user.last_name:
            initial_last_name = self.user.last_name[:1]
        else:
            initial_last_name = ''
        if initial_last_name:
            display_name = '{first_name} {initial_last_name}.'.format(first_name=self.user.first_name,
                                                                      initial_last_name=initial_last_name)
        else:
            display_name = self.user.first_name
        if display_name != self.display_name:
            self.display_name = display_name
            self.save()

    def set_referral_token(self):
        """Set referral token to related user.
        By placing here (account model), the existence of account is assured"""
        if not self.user.referral_token or self.user.referral_token[-6:].isdigit():   # assure to change only when is necessary
            if not self.display_name.strip():
                self.set_display_name()
            if self.display_name.strip():
                token = self.display_name.replace(' ', '').replace('.', '').lower()
                regex = '^' + token + '\d*$'
                regex2 = '^' + token + '(\d*)$'
                existing_token = User.objects.filter(referral_token__iregex=regex)\
                    .values_list('referral_token', flat=True).last()
                if existing_token:
                    res = re.match(regex2, existing_token)
                    num_str = res.groups()[0]
                    if not num_str:
                        num_str = '1'
                    token += str(int(num_str) + 1)
            else:
                for ind in range(20):
                    token = ''.join(generator.generate())
                    regex = '^' + token + '\d*$'
                    regex2 = '^' + token + '(\d*)$'
                    existing_token = User.objects.filter(referral_token__iregex=regex)\
                        .values_list('referral_token', flat=True).last()
                    if existing_token is None:
                        break
                if existing_token:
                    res = re.match(regex2, existing_token)
                    num_str = res.groups()[0]
                    if not num_str:
                        num_str = '1'
                    token += str(int(num_str) + 1)
            self.user.referral_token = token
            self.user.save()


class PhoneNumber(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    number = models.CharField(max_length=50)
    type = models.CharField(max_length=100, choices=PHONE_TYPE_CHOICES)
    verified_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'number']


def get_user_phone(user_acc):
    data = {}
    qs = PhoneNumber.objects.filter(user=user_acc.user)
    if qs.exists():
        phone = qs.all()[0]
        data = {'phoneNumber': phone.number,
                'isVerified': True if phone.verified_at is not None else False,
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

    def __str__(self):
        return f'{self.display_name} ({self.user.email})'


class Instructor(IUserAccount):
    bio_title = models.CharField(max_length=250, blank=True, null=True)
    bio_description = models.TextField(blank=True, null=True)
    social_media_accounts = HStoreField(blank=True, null=True)
    instruments = models.ManyToManyField('lesson.Instrument', through='accounts.InstructorInstruments')
    languages = ArrayField(base_field=models.CharField(max_length=100, blank=True), blank=True, null=True)
    music = ArrayField(base_field=models.CharField(max_length=100, blank=True), blank=True, null=True)
    complete = models.BooleanField(default=False, verbose_name='profile completed')

    bg_status = models.CharField(max_length=100, choices=BG_STATUSES, blank=True, default=BG_STATUS_NOT_VERIFIED,
                                 verbose_name='Background check status')
    interviewed = models.BooleanField(blank=True, default=False)
    job_preferences = ArrayField(blank=True, null=True, base_field=models.CharField(max_length=100))
    place_lessons_preferences = ArrayField(blank=True, null=True, base_field=models.CharField(max_length=100))
    rates = HStoreField(blank=True, null=True)
    studio_address = models.CharField(max_length=250, blank=True, null=True)
    travel_distance = models.CharField(max_length=250, blank=True, null=True)
    video = models.URLField(blank=True, default='')

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

    @property
    def experience_years(self):
        """Return experience years in base to registered employments"""
        elapsed_time = ElapsedTime()
        for employment in self.employment.all():
            if employment.to_year is None:
                today = timezone.now()
                temp_date = get_date_a_month_later(datetime.date(today.year, today.month, today.day))
            else:
                temp_date = get_date_a_month_later(datetime.date(employment.to_year,
                                                                 get_month_integer(employment.to_month),
                                                                 1)
                                                   )
            temp_date = temp_date - datetime.timedelta(days=1)
            elapsed_time.add_time(datetime.date(employment.from_year, get_month_integer(employment.from_month), 1),
                                  temp_date)
        elapsed_time.re_format()
        return elapsed_time.years

    def is_complete(self):
        """Return True if instructor has provided required values for classified his profile as complete"""
        if not (self.user.first_name and self.user.last_name and self.display_name):
            return False
        if not self.birthday or not self.coordinates or not self.avatar:
            return False
        if self.user.reference_requests.count() == 0:   # ToDo: to improve verifying that people fill the reference/form
            return False
        try:
            self.user.phonenumber
        except models.ObjectDoesNotExist:
            return False
        if not self.user.phonenumber.verified_at:
            return False
        if not self.bio_title or not self.bio_description:
            return False
        if self.instruments.count() == 0 or self.instructorlessonsize_set.count() == 0 \
                or self.instructoragegroup_set.count() == 0 or self.instructorlessonrate_set.count() == 0 \
                or self.availability.count() == 0 or self.employment.count() == 0 or self.education.count() == 0:
            return False
        return True

    def update_complete(self):
        """Update value of complete field, if appropriate"""
        curr_value = self.is_complete()
        if curr_value != self.complete:
            Instructor.objects.filter(id=self.id).update(complete=curr_value)   # update to avoid trigger signal for save
            if curr_value:
                add_to_email_list_v2(self.user, [], ['incomplete_profiles'])

    def missing_fields(self):
        """Return a list of fields with absence of values set 'complete' field to False"""
        list_fields = []
        if self.complete:
            return list_fields
        else:
            if not self.user.first_name:
                list_fields.append('first_name')
            if not self.user.last_name:
                list_fields.append('last_name')
            if not self.display_name:
                list_fields.append('display_name')
            if not self.birthday:
                list_fields.append('birthday')
            if not self.coordinates:
                list_fields.append('location')
            if not self.avatar:
                list_fields.append('avatar')
            if not self.video:
                list_fields.append('video')
            if self.user.reference_requests.count() == 0:
                list_fields.append('references')
            try:
                self.user.phonenumber
            except models.ObjectDoesNotExist:
                list_fields.append('phone_number')
            else:
                if not self.user.phonenumber.verified_at:
                    list_fields.append('phone_number')
            if not self.bio_title:
                list_fields.append('bio_title')
            if not self.bio_description:
                list_fields.append('bio_description')
            if self.instruments.count() == 0:
                list_fields.append('instruments')
            if self.instructorlessonsize_set.count() == 0:
                list_fields.append('lesson_size')
            if self.instructoragegroup_set.count() == 0:
                list_fields.append('age_group')
            if self.instructorlessonrate_set.count() == 0:
                list_fields.append('lesson_rate')
            if self.availability.count() == 0:
                list_fields.append('availability')
            if self.employment.count() == 0:
                list_fields.append('employment')
            if self.education.count() == 0:
                list_fields.append('education')
            return list_fields

    def missing_fields_camelcase(self):
        """Same as missing_fields method, but returning strings in camelCase format, and names to use in UI.
        The option of add this method was chosen, in order to avoid usage of many 'if' statements."""
        list_fields = []
        if self.complete:
            return list_fields
        else:
            if not self.user.first_name:
                list_fields.append('firstName')
            if not self.user.last_name:
                list_fields.append('lastName')
            if not self.display_name:
                list_fields.append('displayName')
            if not self.birthday:
                list_fields.append('birthday')
            if not self.coordinates:
                list_fields.append('location')
            if not self.avatar:
                list_fields.append('avatar')
            if not self.video:
                list_fields.append('video')
            if self.user.reference_requests.count() == 0:
                list_fields.append('references')
            try:
                self.user.phonenumber
            except models.ObjectDoesNotExist:
                list_fields.append('isPhoneVerified')
            else:
                if not self.user.phonenumber.verified_at:
                    list_fields.append('isPhoneVerified')
            if not self.bio_title:
                list_fields.append('bioTitle')
            if not self.bio_description:
                list_fields.append('bioDescription')
            if self.instruments.count() == 0:
                list_fields.append('instruments')
            if self.instructorlessonsize_set.count() == 0:
                list_fields.append('lessonSize')
            if self.instructoragegroup_set.count() == 0:
                list_fields.append('ageGroup')
            if self.instructorlessonrate_set.count() == 0:
                list_fields.append('rates')
            if self.availability.count() == 0:
                list_fields.append('availability')
            if self.employment.count() == 0:
                list_fields.append('employment')
            if self.education.count() == 0:
                list_fields.append('education')
            return list_fields

    def lesson_bookings(self):
        """Return a list of lesson bookings related to application of this instructor"""
        from lesson.models import LessonBooking
        return [item for item in LessonBooking.objects.filter(application__instructor=self,
                                                              status__in=[LessonBooking.PAID, LessonBooking.TRIAL])
            .order_by('id')]


class Education(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='education')
    school = models.CharField(max_length=200)
    graduation_year = models.IntegerField()
    degree_type = models.CharField(max_length=100, choices=DEGREE_TYPE_CHOICES)
    field_of_study = models.CharField(max_length=100)
    school_location = models.CharField(max_length=100)
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
    mon8to10 = models.BooleanField(default=False)
    mon10to12 = models.BooleanField(default=False)
    mon12to3 = models.BooleanField(default=False)
    mon3to6 = models.BooleanField(default=False)
    mon6to9 = models.BooleanField(default=False)
    tue8to10 = models.BooleanField(default=False)
    tue10to12 = models.BooleanField(default=False)
    tue12to3 = models.BooleanField(default=False)
    tue3to6 = models.BooleanField(default=False)
    tue6to9 = models.BooleanField(default=False)
    wed8to10 = models.BooleanField(default=False)
    wed10to12 = models.BooleanField(default=False)
    wed12to3 = models.BooleanField(default=False)
    wed3to6 = models.BooleanField(default=False)
    wed6to9 = models.BooleanField(default=False)
    thu8to10 = models.BooleanField(default=False)
    thu10to12 = models.BooleanField(default=False)
    thu12to3 = models.BooleanField(default=False)
    thu3to6 = models.BooleanField(default=False)
    thu6to9 = models.BooleanField(default=False)
    fri8to10 = models.BooleanField(default=False)
    fri10to12 = models.BooleanField(default=False)
    fri12to3 = models.BooleanField(default=False)
    fri3to6 = models.BooleanField(default=False)
    fri6to9 = models.BooleanField(default=False)
    sat8to10 = models.BooleanField(default=False)
    sat10to12 = models.BooleanField(default=False)
    sat12to3 = models.BooleanField(default=False)
    sat3to6 = models.BooleanField(default=False)
    sat6to9 = models.BooleanField(default=False)
    sun8to10 = models.BooleanField(default=False)
    sun10to12 = models.BooleanField(default=False)
    sun12to3 = models.BooleanField(default=False)
    sun3to6 = models.BooleanField(default=False)
    sun6to9 = models.BooleanField(default=False)

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
    one_student = models.BooleanField(default=False)
    small_groups = models.BooleanField(default=False)
    large_groups = models.BooleanField(default=False)


class InstructorAgeGroup(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    children = models.BooleanField(default=False)
    teens = models.BooleanField(default=False)
    adults = models.BooleanField(default=False)
    seniors = models.BooleanField(default=False)


class InstructorLessonRate(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    mins30 = models.DecimalField(max_digits=9, decimal_places=4)
    mins45 = models.DecimalField(max_digits=9, decimal_places=4)
    mins60 = models.DecimalField(max_digits=9, decimal_places=4)
    mins90 = models.DecimalField(max_digits=9, decimal_places=4)


class InstructorPlaceForLessons(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    home = models.BooleanField(default=False)
    studio = models.BooleanField(default=False)
    online = models.BooleanField(default=False)


class InstructorAdditionalQualifications(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    certified_teacher = models.BooleanField(default=False)
    music_therapy = models.BooleanField(default=False)
    music_production = models.BooleanField(default=False)
    ear_training = models.BooleanField(default=False)
    conducting = models.BooleanField(default=False)
    virtuoso_recognition = models.BooleanField(default=False)
    performance = models.BooleanField(default=False)
    music_theory = models.BooleanField(default=False)
    young_children_experience = models.BooleanField(default=False)
    repertoire_selection = models.BooleanField(default=False)


class Student(IUserAccount):
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, blank=True, null=True, related_name='students')

    @property
    def role(self):
        return 'Student'


class TiedStudent(models.Model):
    """Student tied to a Parent, without including an user."""
    parent = models.ForeignKey(Parent, related_name='tied_students', on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    age = models.IntegerField()

    def __str__(self):
        return '{name} ({age} years)'.format(name=self.name, age=self.age)


class StudentDetails(models.Model):
    from lesson.models import Instrument
    user = models.ForeignKey(User, related_name='student_details', on_delete=models.CASCADE)   # student or parent user
    tied_student = models.OneToOneField(TiedStudent, null=True, blank=True, related_name='tied_student_details',
                                        on_delete=models.SET_NULL)
    instrument = models.ForeignKey('lesson.Instrument', on_delete=models.PROTECT)
    skill_level = models.CharField(max_length=50, choices=SKILL_LEVEL_CHOICES)
    lesson_place = models.CharField(max_length=50, choices=PLACE_FOR_LESSONS_CHOICES)
    lesson_duration = models.CharField(max_length=50, choices=LESSON_DURATION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'tied_student'], name='unique_student')
        ]


class Affiliate(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birth_date = models.DateField()
    company_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_referrral_token(self):
        if not self.user.referral_token:   # assure to change only when is necessary
            token = ''
            if self.user.first_name or self.user.last_name:
                if self.user.first_name:
                    token = self.user.first_name.lower()
                if token:
                    if self.user.last_name:
                        token += self.user.last_name[0].lower()
            if token:
                regex = '^' + token + '\d*$'
                regex2 = '^' + token + '(\d*)$'
                existing_token = User.objects.filter(referral_token__iregex=regex) \
                    .values_list('referral_token', flat=True).last()
                if existing_token:
                    res = re.match(regex2, existing_token)
                    num_str = res.groups()[0]
                    if not num_str:
                        num_str = '1'
                    token += str(int(num_str) + 1)
            else:
                for ind in range(20):
                    token = ''.join(generator.generate())
                    regex = '^' + token + '\d*$'
                    regex2 = '^' + token + '(\d*)$'
                    existing_token = User.objects.filter(referral_token__iregex=regex)\
                        .values_list('referral_token', flat=True).last()
                    if existing_token is None:
                        break
                if existing_token:
                    res = re.match(regex2, existing_token)
                    num_str = res.groups()[0]
                    if not num_str:
                        num_str = '1'
                    token += str(int(num_str) + 1)
            self.user.referral_token = token
            self.user.save()


def get_account(user):
    """Get Instructor, Parent or Student instance, related to User instance."""
    if user.get_role() == ROLE_INSTRUCTOR:
        return Instructor.objects.filter(user=user).first()
    if user.get_role() == ROLE_PARENT:
        return Parent.objects.filter(user=user).first()
    return Student.objects.filter(user=user).first()
