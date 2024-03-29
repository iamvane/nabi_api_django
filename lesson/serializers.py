import datetime
import stripe
from dateutil import relativedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from rest_framework import serializers

from accounts.models import Instructor, TiedStudent, get_account
from accounts.serializers import AvailavilitySerializer
from accounts.utils import get_stripe_customer_id
from core.constants import *

from .models import Application, Instrument, Lesson, LessonBooking, LessonRequest, POPULAR_INSTRUMENTS
from .utils import ABREV_DAYS, PACKAGES, RANGE_HOURS_CONV, get_date_time_from_datetime_timezone

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


def validate_timezone(value):
    return value in timezone.pytz.all_timezones


class LessonRequestStudentSerializer(serializers.Serializer):
    """To support lesson request serializers"""
    name = serializers.CharField(max_length=250)
    age = serializers.IntegerField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(data, list):
            data = sorted(data, key=lambda item: item["name"])
        return data


class LessonRequestSerializer(serializers.ModelSerializer):
    """Serializer for create or update a lesson request"""
    instrument = serializers.CharField(max_length=250)
    lessons_duration = serializers.ChoiceField(choices=LESSON_DURATION_CHOICES)
    place_for_lessons = serializers.ChoiceField(choices=PLACE_FOR_LESSONS_CHOICES)
    skill_level = serializers.ChoiceField(choices=SKILL_LEVEL_CHOICES)
    students = serializers.ListField(child=serializers.DictField(), required=False)
    user_id = serializers.IntegerField(source='user.id')
    date = serializers.DateField(format='%Y-%m-%d', required=False)
    time = serializers.TimeField(format='%H:%M', required=False)
    timezone = serializers.CharField(max_length=50, validators=[validate_timezone], required=False)

    class Meta:
        model = LessonRequest
        fields = ('user_id', 'title', 'message', 'instrument', 'lessons_duration', 'travel_distance',
                  'place_for_lessons', 'skill_level', 'students', 'date', 'time', 'timezone',
                  'gender', 'language', 'trial_proposed_datetime', 'trial_proposed_timezone')

    def to_internal_value(self, data):
        keys = dict.fromkeys(data, 1)
        new_data = {}
        if keys.get('user_id'):
            new_data['user_id'] = data.get('user_id')
        if keys.get('requestTitle'):
            new_data['title'] = data.get('requestTitle')
        if keys.get('requestMessage'):
            new_data['message'] = data.get('requestMessage')
        if keys.get('instrument'):
            new_data['instrument'] = data.get('instrument')
        if keys.get('lessonDuration'):
            new_data['lessons_duration'] = data.get('lessonDuration')
        if keys.get('travelDistance'):
            new_data['travel_distance'] = data.get('travelDistance')
        if keys.get('placeForLessons'):
            new_data['place_for_lessons'] = data.get('placeForLessons')
        if keys.get('skillLevel'):
            new_data['skill_level'] = data.get('skillLevel')
        if keys.get('students'):
            new_data['students'] = data.get('students')
        if keys.get('date'):
            new_data['date'] = data.get('date')
        if keys.get('time'):
            new_data['time'] = data.get('time')
        if keys.get('timezone'):
            new_data['timezone'] = data.get('timezone')
        if keys.get('gender'):
            new_data['gender'] = data.get('gender')
        if keys.get('language'):
            new_data['language'] = data.get('language')
        return super().to_internal_value(new_data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.instance:   # when calls to create (POST)
            if self.context['is_parent'] and not attrs.get('students'):
                raise serializers.ValidationError('students data must be provided')
            if attrs['place_for_lessons'] == 'studio' and not attrs.get('travel_distance'):
                raise serializers.ValidationError('travel_distance value must be provided')
            there_is_one = attrs.get('date') or attrs.get('time') or attrs.get('timezone')
            there_is_all = attrs.get('date') and attrs.get('time') and attrs.get('timezone')
            user = User.objects.get(id=attrs['user']['id'])
            if (there_is_one and not there_is_all) or (user.lesson_bookings.count() == 0 and not there_is_all):
                raise serializers.ValidationError("Data for schedule trial lesson is missing")
        else:
            if self.instance.status == LESSON_REQUEST_CLOSED:
                raise serializers.ValidationError('Closed Lesson Request can not be edited')
            if attrs.get('place_for_lessons') == 'studio' and (
                    (self.instance.travel_distance is None and attrs.get('travel_distance') is None)
                    or (self.instance.travel_distance is not None and 'travel_distance' in attrs.keys()
                        and attrs.get('travel_distance') is None)
            ):
                raise serializers.ValidationError('travel_distance value must be provided')
            if attrs.get('date') or attrs.get('time') or attrs.get('timezone'):
                raise serializers.ValidationError("Proposed schedule for trial lesson can't be changed here")
        return attrs

    def create(self, validated_data):
        instrument, _ = Instrument.objects.get_or_create(name=validated_data.pop('instrument'))
        validated_data['user_id'] = validated_data.get('user', {}).get('id')
        validated_data.pop('user')
        validated_data['instrument_id'] = instrument.id
        if validated_data.get('date'):
            time_zone = validated_data.pop('timezone')
            tz_offset = datetime.datetime.now(timezone.pytz.timezone(time_zone)).strftime('%z')
            validated_data['trial_proposed_datetime'] = f"{validated_data.pop('date')} {validated_data.pop('time')}{tz_offset}"
            validated_data['trial_proposed_timezone'] = time_zone
        if self.context['is_parent']:
            parent_obj = User.objects.get(id=validated_data['user_id']).parent
            students_data = validated_data.pop('students')
            res = super().create(validated_data)
            for student_item in students_data:
                tied_student, _ = TiedStudent.objects.get_or_create(name=student_item['name'],
                                                                    age=student_item['age'],
                                                                    parent=parent_obj)
                res.students.add(tied_student)
            return res
        else:
            return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('students'):
            student_data = validated_data.pop('students')
            if not self.context['is_parent']:
                student_data = None
        else:
            student_data = None
        if validated_data['user']:
            user_data = validated_data.pop('user')
            validated_data['user_id'] = user_data['id']
        if validated_data.get('instrument'):
            instrument, _ = Instrument.objects.get_or_create(name=validated_data.pop('instrument'))
            validated_data['instrument_id'] = instrument.id
        if validated_data:
            super().update(instance, validated_data)
            instance.refresh_from_db()
        if student_data:   # if student_data, user is parent (checked at beginning)
            parent = User.objects.get(id=validated_data['user_id']).parent
            if isinstance(student_data, list):
                ts_list = []
                for student_item in student_data:
                    student_item['parent'] = parent
                    ts, _ = TiedStudent.objects.get_or_create(**student_item)
                    ts_list.append(ts)
                instance.students.set(ts_list)
            else:
                ts, _ = TiedStudent.objects.get_or_create(name=student_data['name'], age=student_data['age'],
                                                          parent=parent)
                instance.students.add(ts)
        return instance


class LessonRequestDetailSerializer(serializers.ModelSerializer):
    """Serializer for fetching only. Call made by parent or student."""
    instrument = serializers.CharField(read_only=True, source='instrument.name')
    lessonDuration = serializers.CharField(max_length=100, source='lessons_duration', read_only=True)
    placeForLessons = serializers.CharField(max_length=100, source='place_for_lessons', read_only=True)
    requestMessage = serializers.CharField(max_length=100000, source='message', read_only=True)
    requestTitle = serializers.CharField(max_length=100, source='title', read_only=True)
    skillLevel = serializers.CharField(max_length=100, source='skill_level', read_only=True)
    travelDistance = serializers.IntegerField(source='travel_distance', read_only=True)
    students = LessonRequestStudentSerializer(many=True, read_only=True)
    date = serializers.CharField(max_length=10, required=False)
    time = serializers.CharField(max_length=5, required=False)
    timezone = serializers.CharField(max_length=50, required=False)
    availability = serializers.JSONField(source='trial_availability_schedule')

    class Meta:
        model = LessonRequest
        fields = ('id', 'instrument', 'requestMessage', 'requestTitle', 'lessonDuration', 'travelDistance',
                  'placeForLessons', 'skillLevel', 'status', 'students', 'date', 'time', 'timezone', 'availability',
                  'gender', 'language')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.students.count() == 0:
            data.pop('students')
            data['studentDetails'] = [{'name': instance.user.first_name, 'age': instance.user.student.age}]
        else:
            data['studentDetails'] = data.pop('students')
        if instance.trial_proposed_datetime:
            account = get_account(self.context['user'])
            if account.timezone:
                data['timezone'] = account.timezone
            else:
                data['timezone'] = account.get_timezone_from_location_zipcode()
            data['date'], data['time'] = get_date_time_from_datetime_timezone(instance.trial_proposed_datetime,
                                                                              data['timezone'])
        return data


class LessonRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for create a lesson request"""
    instrument = serializers.CharField(max_length=250, required=False)
    skillLevel = serializers.CharField(source='skill_level', required=False)
    studentId = serializers.CharField(max_length=250, required=False)
    availability = serializers.JSONField(source='trial_availability_schedule', required=True)
    placeForLessons = serializers.CharField(max_length=100, source='place_for_lessons',
                                            required=False, default=PLACE_FOR_LESSONS_ONLINE)
    lessonsDuration = serializers.CharField(max_length=100, source='lessons_duration',
                                            required=False, default=LESSON_DURATION_30)

    class Meta:
        model = LessonRequest
        fields = ('user', 'instrument', 'skillLevel', 'studentId', 'availability', 'placeForLessons', 'lessonsDuration',
                  'gender', 'language')

    def validate_studentId(self, value):
        if not TiedStudent.objects.filter(parent__user_id=self.initial_data['user'], id=value).exists():
            raise serializers.ValidationError('This parent has not student with provided id')
        else:
            return value

    def validate_availability(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Availability value must be a list')
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError('Availability value must be a dictionary')
            if 'day' not in item.keys() or 'timeframe' not in item.keys():
                raise serializers.ValidationError('Dictionaries in availability must include day and timeframe keys')
            if item.get('day') not in ABREV_DAYS:
                raise serializers.ValidationError('An invalid value of day was provided')
            if not RANGE_HOURS_CONV.get(item.get('timeframe', '--')):
                raise serializers.ValidationError('An invalid value of timeframe was provided')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.instance:   # when calls to create (POST)
            if attrs.get('user').is_parent() and not attrs.get('studentId'):
                raise serializers.ValidationError('Student id must be provided')
            if ('instrument' in attrs.keys()) ^ ('skill_level' in attrs.keys()):
                raise serializers.ValidationError('Inconsistent: instrument and skillLevel should be provided together or not provided')
        return attrs

    def create(self, validated_data):
        if validated_data.get('instrument'):
            instrument, _ = Instrument.objects.get_or_create(name=validated_data.pop('instrument'))
            validated_data['instrument'] = instrument
        if validated_data['user'].is_parent():
            tied_student = TiedStudent.objects.filter(parent=validated_data['user'].parent,
                                                      id=validated_data.pop('studentId')).first()
            if not validated_data.get('instrument'):
                validated_data['instrument'] = tied_student.tied_student_details.instrument
                validated_data['skill_level'] = tied_student.tied_student_details.skill_level
            res = super().create(validated_data)
            res.students.add(tied_student)
            return res
        else:
            student_details = validated_data['user'].student_details.first()
            if not validated_data.get('instrument'):
                validated_data['instrument'] = student_details.instrument
                validated_data['skill_level'] = student_details.skill_level
            return super().create(validated_data)


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creation of application"""
    instructor_id = serializers.IntegerField()
    request_id = serializers.IntegerField()

    class Meta:
        model = Application
        fields = ('request_id', 'rate', 'message', 'instructor_id')

    def to_internal_value(self, data):
        new_data = data.copy()
        if new_data.get('requestId'):
            new_data['request_id'] = new_data.pop('requestId')
        return super().to_internal_value(new_data)


class ApplicationListSerializer(serializers.ModelSerializer):
    """Serializer for get a list of application made by current instructor"""
    display_name = serializers.SerializerMethodField()   # display_name of requestor (student/parent)
    id = serializers.IntegerField(read_only=True)
    request_id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=100, source='request.title', read_only=True)
    date_applied = serializers.DateTimeField(format='%Y-%m-%d', source='created_at')

    class Meta:
        model = Application
        fields = ('display_name', 'id', 'request_id', 'seen', 'title', 'date_applied')

    def get_display_name(self, instance):
        """Get display name of requestor"""
        account = get_account(instance.request.user)
        return account.display_name

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['displayName'] = data.pop('display_name')
        data['requestId'] = data.pop('request_id')
        data['dateApplied'] = data.pop('date_applied')
        return data


class ApplicationItemSerializer(serializers.ModelSerializer):
    """Serializer to be used in a list of lesson request's applications"""
    applicationId = serializers.IntegerField(source='id', read_only=True)
    age = serializers.IntegerField(source='instructor.age', read_only=True)
    applicationMessage = serializers.CharField(source='message', read_only=True)
    applicationRate = serializers.DecimalField(max_digits=9, decimal_places=4, source='rate', read_only=True)
    availability = AvailavilitySerializer(source='instructor.availability', read_only=True)
    avatar = serializers.SerializerMethodField()
    video = serializers.CharField(max_length=200, source='instructor.video', read_only=True)
    backgroundCheckStatus = serializers.CharField(max_length=100, source='instructor.bg_status', read_only=True)
    displayName = serializers.CharField(max_length=100, source='instructor.display_name', read_only=True)
    instructorId = serializers.IntegerField(source='instructor.id', read_only=True)
    reviews = serializers.DictField(source='instructor.get_review_dict')
    yearsOfExperience = serializers.IntegerField(source='instructor.years_of_experience', read_only=True)

    class Meta:
        model = Application
        fields = ('instructorId', 'applicationId', 'applicationMessage', 'applicationRate', 'age', 'availability',
                  'avatar', 'video', 'backgroundCheckStatus', 'displayName', 'reviews', 'yearsOfExperience')

    def get_avatar(self, instance):
        if instance.instructor.avatar:
            return instance.instructor.avatar.url
        else:
            return ''


class MinimalApplicationSerializer(serializers.ModelSerializer):
    """Serializer to display data to instructor"""
    applicationId = serializers.IntegerField(source='id', read_only=True)
    applicationRate = serializers.DecimalField(max_digits=9, decimal_places=4, source='rate', read_only=True)
    displayName = serializers.CharField(max_length=100, source='instructor.display_name', read_only=True)
    requestId = serializers.IntegerField(source='request.id', read_only=True)

    class Meta:
        model = Application
        fields = ('applicationId', 'applicationRate', 'displayName', 'requestId', )


class LessonRequestItemSerializer(serializers.ModelSerializer):
    """Serializer for get data of a lesson request, to build a list; call made by an instructor mostly time."""
    avatar = serializers.CharField(max_length=500, source='*', read_only=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    display_name = serializers.SerializerMethodField()
    instrument = serializers.CharField(max_length=250, source='instrument.name', read_only=True)
    location = serializers.CharField(max_length=150, source='*', read_only=True)
    role = serializers.CharField(max_length=100, source='user.get_role', read_only=True)
    students = LessonRequestStudentSerializer(many=True, read_only=True)
    distance = serializers.FloatField(source='distance.mi', read_only=True)
    applications_received = serializers.SerializerMethodField()
    applied = serializers.SerializerMethodField()
    date = serializers.CharField(max_length=10, required=False)
    time = serializers.CharField(max_length=5, required=False)
    timezone = serializers.CharField(max_length=50, required=False)

    class Meta:
        model = LessonRequest
        fields = ('avatar', 'created_at', 'display_name', 'distance', 'id', 'instrument',  'lessons_duration',
                  'location', 'message', 'place_for_lessons', 'role', 'skill_level', 'students', 'title',
                  'gender', 'language', 'applications_received', 'applied', 'date', 'time', 'timezone')

    def get_applications_received(self, instance):
        return instance.applications.count()

    def get_applied(self, instance):
        if self.context.get('user'):
            return instance.applications.filter(instructor=self.context['user'].instructor).exists()
        else:
            return False

    def get_display_name(self, instance):
        account = get_account(instance.user)
        if account:
            return account.display_name
        else:
            return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        new_data = {'createdAt': data.get('created_at'),
                    'displayName': data.get('display_name'),
                    'distance': data.get('distance'),
                    'id': data.get('id'),
                    'instrument': data.get('instrument'),
                    'lessonDuration': data.get('lessons_duration'),
                    'gender': data.get('gender'),
                    'language': data.get('language'),
                    'requestMessage': data.get('message'),
                    'placeForLessons': data.get('place_for_lessons'),
                    'skillLevel': data.get('skill_level'),
                    'requestTitle': data.get('title'),
                    'role': data.get('role'),
                    'applicationsReceived': data.get('applications_received'),
                    'applied': data.get('applied')
                    }
        if data.get('role') == ROLE_STUDENT:
            new_data['studentDetails'] = [{'name': instance.user.first_name, 'age': instance.user.student.age}]
            try:
                new_data['avatar'] = instance.user.student.avatar.url
            except ValueError:
                new_data['avatar'] = ''
            new_data['location'] = instance.user.student.location
        else:
            new_data['studentDetails'] = data.get('students')
            try:
                new_data['avatar'] = instance.user.parent.avatar.url
            except ValueError:
                new_data['avatar'] = ''
            new_data['location'] = instance.user.parent.location
        if instance.trial_proposed_datetime:
            if self.context.get('user'):
                account = get_account(self.context['user'])
                if account.timezone:
                    new_data['timezone'] = account.timezone
                else:
                    new_data['timezone'] = account.get_timezone_from_location_zipcode()
            else:
                new_data['timezone'] = 'US/Eastern'
            new_data['date'], new_data['time'] = get_date_time_from_datetime_timezone(instance.trial_proposed_datetime,
                                                                                      new_data['timezone'])
        return new_data


class LessonRequestListQueryParamsSerializer(serializers.Serializer):
    """Serializer to be used with GET parameters in lesson request list endpoint."""
    distance = serializers.IntegerField(min_value=0, required=False)
    instrument = serializers.CharField(max_length=250, required=False)
    location = serializers.CharField(max_length=200, required=False)
    age = serializers.ChoiceField(choices=AGE_CHOICES, required=False)
    place_for_lessons = serializers.CharField(max_length=200, required=False)

    def to_internal_value(self, data):
        new_data = data.copy()
        keys = dict.fromkeys(data, 1)
        if keys.get('placeForLessons'):
            new_data['place_for_lessons'] = new_data.pop('placeForLessons')
        return super().to_internal_value(new_data)

    def validate_location(self, value):
        try:
            [lat, lng] = value.split(',')
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            raise serializers.ValidationError('Location value should have format latitude,longitude, both float values')
        if lat < -90 or lat > 90:
            raise serializers.ValidationError('Wrong latitude value')
        if lng < -180 or lng >= 180:
            raise serializers.ValidationError('Wrong longitude value')
        return lat, lng

    def validate_place_for_lessons(self, value):
        places = value.split(',')
        valid_places = [item[0] for item in PLACE_FOR_LESSONS_CHOICES]
        for place in places:
            if place not in valid_places:
                raise serializers.ValidationError('{} is not a valid placeForLesson value'.format(place))
        return places


class LessonRequestListItemSerializer(serializers.ModelSerializer):
    """Serializer for get data of a lesson request; call made by an instructor"""
    avatar = serializers.SerializerMethodField()
    displayName = serializers.SerializerMethodField()
    instrument = serializers.CharField(max_length=250, source='instrument.name', read_only=True)
    lessonDuration = serializers.CharField(max_length=100, source='lessons_duration', read_only=True)
    location = serializers.SerializerMethodField()
    placeForLessons = serializers.CharField(max_length=100, source='place_for_lessons', read_only=True)
    requestTitle = serializers.CharField(max_length=100, source='title', read_only=True)
    requestMessage = serializers.CharField(source='message', read_only=True)
    skillLevel = serializers.CharField(max_length=100, source='skill_level', read_only=True)
    studentDetails = serializers.SerializerMethodField()
    application = serializers.SerializerMethodField()
    applied = serializers.SerializerMethodField()
    availability = serializers.JSONField(source='trial_availability_schedule')
    timezone = serializers.SerializerMethodField()
    additionalNotes = serializers.SerializerMethodField()

    class Meta:
        model = LessonRequest
        fields = ('id', 'avatar', 'displayName', 'instrument',  'lessonDuration', 'location', 'requestMessage',
                  'placeForLessons', 'skillLevel', 'studentDetails', 'requestTitle', 'application', 'applied',
                  'gender', 'language', 'status', 'availability', 'timezone', 'additionalNotes')

    def get_avatar(self, instance):
        account = get_account(instance.user)
        if account and account.avatar:
            return account.avatar.url
        else:
            return ''

    def get_application(self, instance):
        if self.context.get('user') and self.context.get('user').is_instructor():
            application = Application.objects.filter(request=instance, instructor=self.context.get('user').instructor).last()
            if application:
                return {'dateApplied': application.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'rate': application.rate,
                        'message': application.message}
        return {}

    def get_applied(self, instance):
        if self.context.get('user') and self.context.get('user').is_instructor():
            return instance.acceptances.filter(instructor=self.context.get('user').instructor).exists()
        return False

    def get_displayName(self, instance):
        account = get_account(instance.user)
        if account:
            return account.display_name
        else:
            return ''

    def get_location(self, instance):
        account = get_account(instance.user)
        if account:
            location_tuple = account.get_location(result_type='tuple')
            if location_tuple:
                return '{}, {}'.format(location_tuple[2], location_tuple[1])
        return ''

    def get_studentDetails(self, instance):
        if instance.user.is_parent():
            student_list = []
            for student in instance.students.all():
                student_list.append({'name': student.name, 'age': student.age})
            return student_list
        else:
            return [{'name': instance.user.first_name, 'age': instance.user.student.age}]

    def get_timezone(self, instance):
        account = get_account(instance.user)
        if account:
            if account.timezone:
                return account.timezone
            else:
                return account.get_timezone_from_location_zipcode()
        else:
            return ''

    def get_additionalNotes(self, instance):
        if instance.user.is_parent():
            stu = instance.students.last()
            stu_details = stu.tied_student_details
        else:
            stu_details = instance.user.student_details.last()
        return stu_details.notes


class LessonBookingRegisterSerializer(serializers.Serializer):
    """Serializer for registration of a lesson booking"""
    applicationId = serializers.IntegerField(required=False)
    userId = serializers.IntegerField()
    package = serializers.ChoiceField(choices=list(PACKAGES.keys()))
    paymentMethodCode = serializers.CharField(max_length=500)

    def validate_userId(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('There is not User with provided id')
        else:
            return value

    def validate_applicationId(self, value):
        if not Application.objects.filter(id=value).exists():
            raise serializers.ValidationError('There is not Application with provided id')
        else:
            return value

    def validate_paymentMethodCode(self, value):
        user = User.objects.get(id=self.initial_data['userId'])
        customer_id = get_stripe_customer_id(user)
        try:
            pm = stripe.PaymentMethod.retrieve(value)
        except stripe.error.InvalidRequestError:
            raise serializers.ValidationError('There is not payment method with provided code')
        if not customer_id or not pm or (pm.get('customer', '') != customer_id):
            raise serializers.ValidationError('Wrong payment method')
        return value

    def validate_package(self, value):
        user = User.objects.get(id=self.initial_data['userId'])
        if user.lesson_bookings.count() == 0:
            self.initial_data['package'] = PACKAGE_TRIAL
        elif value == PACKAGE_TRIAL:
            raise serializers.ValidationError('Trial is not valid package for this user')
        return value


class LessonBookingStudentDashboardSerializer(serializers.ModelSerializer):
    """Serializer to get data of lesson booking created by a student"""
    applicationId = serializers.SerializerMethodField()
    instrument = serializers.SerializerMethodField()
    skillLevel = serializers.SerializerMethodField()
    instructor = serializers.CharField(max_length=100, source='instructor.display_name', read_only=True)
    lessonsRemaining = serializers.IntegerField(source='remaining_lessons', read_only=True)
    students = serializers.SerializerMethodField()

    class Meta:
        model = LessonBooking
        fields = ('applicationId', 'instrument', 'skillLevel', 'instructor', 'lessonsRemaining', 'students')

    def get_students(self, instance):
        return [{'name': instance.user.first_name, 'age': instance.user.student.age}]

    def get_applicationId(self, instance):
        if instance.application:
            return instance.application.id
        else:
            return None

    def get_instrument(self, instance):
        if instance.application:
            return instance.application.request.instrument.name
        else:
            return instance.request.instrument.name

    def get_skillLevel(self, instance):
        if instance.application:
            return instance.application.request.skill_level
        else:
            return instance.request.skill_level


class LessonBookingParentDashboardSerializer(serializers.ModelSerializer):
    """Serializer to get data of lesson booking created by a parent"""
    applicationId = serializers.SerializerMethodField()
    instrument = serializers.SerializerMethodField()
    skillLevel = serializers.SerializerMethodField()
    instructor = serializers.CharField(max_length=100, source='instructor.display_name', read_only=True)
    lessonsRemaining = serializers.IntegerField(source='remaining_lessons', read_only=True)
    students = serializers.SerializerMethodField()

    class Meta:
        model = LessonBooking
        fields = ('applicationId', 'instrument', 'skillLevel', 'instructor', 'lessonsRemaining', 'students')

    def get_applicationId(self, instance):
        if instance.application:
            return instance.application.id
        else:
            return None

    def get_instrument(self, instance):
        if instance.application:
            return instance.application.request.instrument.name
        else:
            return instance.request.instrument.name

    def get_skillLevel(self, instance):
        if instance.application:
            return instance.application.request.skill_level
        else:
            return instance.request.skill_level

    def get_students(self, instance):
        if instance.application:
            ser = LessonRequestStudentSerializer(instance.application.request.students, many=True)
            return ser.data
        else:
            ser = LessonRequestStudentSerializer(instance.request.students, many=True)
            return ser.data


class LessonRequestStudentDashboardSerializer(serializers.ModelSerializer):
    instrument = serializers.CharField(read_only=True, source='instrument.name')
    lessonDuration = serializers.CharField(max_length=100, source='lessons_duration', read_only=True)
    placeForLessons = serializers.CharField(max_length=100, source='place_for_lessons', read_only=True)
    requestMessage = serializers.CharField(max_length=100000, source='message', read_only=True)
    requestTitle = serializers.CharField(max_length=100, source='title', read_only=True)
    skillLevel = serializers.CharField(max_length=100, source='skill_level', read_only=True)
    studentDetails = serializers.SerializerMethodField()
    applications = serializers.IntegerField(source='applications.count', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = LessonRequest
        fields = ('id', 'instrument', 'lessonDuration', 'placeForLessons', 'requestMessage', 'requestTitle',
                  'studentDetails', 'skillLevel', 'applications', 'createdAt')

    def get_studentDetails(self, instance):
        return [{'name': instance.user.first_name, 'age': instance.user.student.age}]


class LessonRequestParentDashboardSerializer(serializers.ModelSerializer):
    instrument = serializers.CharField(read_only=True, source='instrument.name')
    lessonDuration = serializers.CharField(max_length=100, source='lessons_duration', read_only=True)
    placeForLessons = serializers.CharField(max_length=100, source='place_for_lessons', read_only=True)
    requestMessage = serializers.CharField(max_length=100000, source='message', read_only=True)
    requestTitle = serializers.CharField(max_length=100, source='title', read_only=True)
    skillLevel = serializers.CharField(max_length=100, source='skill_level', read_only=True)
    studentDetails = LessonRequestStudentSerializer(source='students', many=True, read_only=True)
    applications = serializers.IntegerField(source='applications.count', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = LessonRequest
        fields = ('id', 'instrument', 'lessonDuration', 'placeForLessons', 'requestMessage', 'requestTitle',
                  'studentDetails', 'skillLevel', 'applications', 'createdAt')


class InstructorDashboardSerializer(serializers.ModelSerializer):
    """Serializer to get data about instructor, for display in dashboard"""
    class LessonBookingSerializer(serializers.ModelSerializer):
        bookingId = serializers.IntegerField(source='id', read_only=True)
        instrument = serializers.SerializerMethodField()
        lessonsBooked = serializers.IntegerField(source='quantity', read_only=True)
        lessonsRemaining = serializers.SerializerMethodField()
        skillLevel = serializers.SerializerMethodField()
        studentName = serializers.CharField(max_length=30, required=False, read_only=True)
        age = serializers.IntegerField(required=False, read_only=True)
        parent = serializers.CharField(max_length=30, required=False, read_only=True)
        students = serializers.ListField(required=False, read_only=True)
        lastLessonId = serializers.SerializerMethodField()

        class Meta:
            model = LessonBooking
            fields = ('bookingId', 'instrument', 'lessonsBooked', 'lessonsRemaining', 'skillLevel',
                      'studentName', 'age', 'parent', 'students', 'lastLessonId')

        def get_instrument(self, instance):
            if instance.tied_student:
                if hasattr(instance.tied_student, 'tied_student_details') \
                        and instance.tied_student.tied_student_details.instrument:
                    return instance.tied_student.tied_student_details.instrument.name
            else:
                student_details = instance.user.student_details.first()
                if student_details and student_details.instrument:
                    return student_details.instrument.name
            return ''

        def get_lessonsRemaining(self, instance):
            return instance.remaining_lessons() \
                   + Lesson.objects.filter(~Q(status=Lesson.COMPLETE),
                                           booking__in=LessonBooking.objects.filter(user=instance.user,
                                                                                    tied_student=instance.tied_student)
                                           .exclude(id=instance.id)
                                           ).count()

        def get_skillLevel(self, instance):
            if instance.tied_student:
                if hasattr(instance.tied_student, 'tied_student_details'):
                    return instance.tied_student.tied_student_details.skill_level
            else:
                student_details = instance.user.student_details.first()
                if student_details:
                    return student_details.skill_level
            return None

        def get_lastLessonId(self, instance):
            lesson = Lesson.objects.filter(booking__in=LessonBooking.objects.filter(user=instance.user,
                                                                                    tied_student=instance.tied_student),
                                           status=Lesson.SCHEDULED, scheduled_datetime__lt=timezone.now())\
                .order_by('scheduled_datetime').first()
            if lesson:
                return lesson.id
            else:
                return None

        def to_representation(self, instance):
            data = super().to_representation(instance)
            if instance.user.is_parent():
                data['parent'] = instance.user.parent.display_name
                if instance.tied_student:
                    data['students'] = [{'name': instance.tied_student.name, 'age': instance.tied_student.age}]
                else:
                    data['students'] = []
            else:
                data['studentName'] = instance.user.student.display_name
                data['age'] = instance.user.student.age
            return data

    backgroundCheckStatus = serializers.CharField(max_length=100, source='bg_status', read_only=True)
    missingFields = serializers.ListField(source='missing_fields_camelcase')
    lessons = serializers.SerializerMethodField()
    zoomLink = serializers.URLField(source='zoom_link')

    class Meta:
        model = Instructor
        fields = ('id', 'backgroundCheckStatus', 'complete', 'missingFields', 'zoomLink', 'lessons', )

    def get_lessons(self, instance):
        list_bookings = []
        user_id_ant = student_id_ant = 0
        for booking in instance.bookings.filter(status__in=[LessonBooking.PAID, LessonBooking.TRIAL])\
                .order_by('user', 'tied_student', '-id'):
            if booking.user_id != user_id_ant or booking.tied_student_id != student_id_ant:
                list_bookings.append(booking)
                user_id_ant = booking.user_id
                student_id_ant = booking.tied_student_id
        ser = self.LessonBookingSerializer(list_bookings, many=True)
        return ser.data


class LessonRequestInstructorDashboardSerializer(serializers.ModelSerializer):
    """Serializer to get data of lesson requests available to apply by an instructor"""
    requestTitle = serializers.CharField(max_length=100, source='title', read_only=True)
    displayName = serializers.SerializerMethodField()
    distance = serializers.FloatField(source='distance.mi', read_only=True)
    instrument = serializers.CharField(max_length=250, source='instrument.name', read_only=True)
    lessonDuration = serializers.ChoiceField(LESSON_DURATION_CHOICES, source='lessons_duration', read_only=True)
    placeForLessons = serializers.ChoiceField(PLACE_FOR_LESSONS_CHOICES, source='place_for_lessons', read_only=True)
    skillLevel = serializers.CharField(max_length=100, source='skill_level', read_only=True)
    elapsedTime = serializers.SerializerMethodField()
    role = serializers.CharField(max_length=100, source='user.get_role', read_only=True)
    applicationsReceived = serializers.IntegerField(source='applications.count', read_only=True)
    studentDetails = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = LessonRequest
        fields = ('id', 'requestTitle', 'displayName', 'distance', 'instrument', 'lessonDuration',
                  'placeForLessons', 'skillLevel', 'elapsedTime', 'role', 'applicationsReceived', 'studentDetails',
                  'avatar', 'location')

    def get_displayName(self, instance):
        if instance.user.is_parent():
            return instance.user.parent.display_name
        else:
            return instance.user.student.display_name

    def get_studentDetails(self, instance):
        if instance.user.is_parent():
            return [{'name': item.name, 'age': item.age} for item in instance.students.all()]
        else:
            return {'age': instance.user.student.age}

    def get_avatar(self, instance):
        if instance.user.is_parent():
            if instance.user.parent.avatar:
                return instance.user.parent.avatar.url
            else:
                return ''
        else:
            if instance.user.student.avatar:
                return instance.user.student.avatar.url
            else:
                return ''

    def get_location(self, instance):
        if instance.user.is_parent():
            return instance.user.parent.get_location()
        else:
            return instance.user.student.get_location()

    def get_elapsedTime(self, instance):
        elapsed_time = relativedelta.relativedelta(timezone.now(), instance.created_at)
        if elapsed_time.years > 0:
            elapsed_str = '{} years'.format(elapsed_time.years)
        elif elapsed_time.months > 0:
            elapsed_str = '{} months'.format(elapsed_time.months)
        elif elapsed_time.days > 0:
            elapsed_str = '{} days'.format(elapsed_time.days)
        elif elapsed_time.hours > 0:
            elapsed_str = '{} hours'.format(elapsed_time.hours)
        elif elapsed_time.minutes > 0:
            elapsed_str = '{} minutes'.format(elapsed_time.minutes)
        else:
            elapsed_str = '{} seconds'.format(elapsed_time.seconds)
        return elapsed_str

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['distance'] is not None:
            data['distance'] = format(data['distance'], '.2f')
        return data


class CreateLessonSerializer(serializers.ModelSerializer):
    """Serializer for create a Lesson instance, when a Booking was created already"""
    bookingId = serializers.IntegerField(source='booking_id')
    date = serializers.DateField(format='%Y-%m-%d')
    time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Lesson
        fields = ('bookingId', 'date', 'time', )

    def validate(self, attrs):
        booking = LessonBooking.objects.get(id=attrs['booking_id'])
        if booking.quantity - booking.lessons.count() == 0:
            raise serializers.ValidationError('There is not available lessons')
        return attrs

    def create(self, validated_data):
        booking = LessonBooking.objects.get(id=validated_data['booking_id'])
        if booking.status == PACKAGE_TRIAL:
            validated_data['status'] = Lesson.SCHEDULED
        account = get_account(booking.user)
        time_zone = account.get_timezone_from_location_zipcode()
        tz_offset = datetime.datetime.now(timezone.pytz.timezone(time_zone)).strftime('%z')
        validated_data['scheduled_datetime'] = f"{validated_data.pop('date')} {validated_data.pop('time')}{tz_offset}"
        validated_data['scheduled_timezone'] = time_zone
        return super().create(validated_data)


class UpdateLessonSerializer(serializers.ModelSerializer):
    """To update a Lesson instance"""
    id = serializers.IntegerField(read_only=True)
    grade = serializers.IntegerField(min_value=1, max_value=3)
    date = serializers.DateField(format='%Y-%m-%d')
    time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Lesson
        fields = ('id', 'grade', 'comment', 'date', 'status', 'time', 'scheduled_datetime')

    def validate_grade(self, value):
        if self.instance.status in (Lesson.MISSED, Lesson.COMPLETE):
            raise serializers.ValidationError('This lesson can not be graded')
        else:
            return value

    def validate_status(self, value):
        valid_statuses = (Lesson.SCHEDULED, Lesson.MISSED)
        if self.instance.status not in valid_statuses or value not in valid_statuses:
            raise serializers.ValidationError('That change of status is not allowed')
        else:
            return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        keys = dict.fromkeys(attrs, 1)
        # verify data existence for date/time schedule
        if (keys.get('date', 0) + keys.get('time', 0)) == 1:
            raise serializers.ValidationError('Incomplete data for re-schedule the lesson')
        account = get_account(self.instance.booking.user)
        if attrs.get("date") and attrs.get("time"):
            time_zone = account.get_timezone_from_location_zipcode()
            tz_offset = datetime.datetime.now(timezone.pytz.timezone(time_zone)).strftime('%z')
            attrs['scheduled_datetime'] = f'{attrs.pop("date")} {attrs.pop("time")}{tz_offset}'
            attrs['scheduled_timezone'] = time_zone
        # verify data existence for grade a lesson
        if (keys.get('grade', 0) + keys.get('comment', 0)) == 1:
            raise serializers.ValidationError('Incomplete data to grade the lesson')
        if self.instance.status == Lesson.COMPLETE:
            raise serializers.ValidationError('This lesson could not be updated')
        return attrs

    def update(self, instance, validated_data):
        if 'grade' in validated_data.keys():
            validated_data['status'] = Lesson.COMPLETE
        elif 'scheduled_timezone' in validated_data.keys():
            validated_data['status'] = Lesson.SCHEDULED
        return super().update(instance, validated_data)


class ScheduledLessonSerializer(serializers.ModelSerializer):
    """To display info of scheduled Lesson"""
    date = serializers.DateField(format='%Y-%m-%d')
    time = serializers.TimeField(format='%H:%M')
    timezone = serializers.SerializerMethodField()
    instructor = serializers.SerializerMethodField()
    studentDetails = serializers.SerializerMethodField()
    zoomLink = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ('id', 'date', 'time', 'timezone', 'studentDetails', 'instructor', 'zoomLink', )

    def get_instructor(self, instance):
        if instance.instructor:
            return instance.instructor.display_name
        elif instance.booking.instructor:
            return instance.booking.instructor.display_name
        else:
            return ''

    def get_zoomLink(self, instance):
        if instance.instructor:
            return instance.instructor.zoom_link
        else:
            return ''

    def to_representation(self, instance):
        account = get_account(self.context['user'])
        if account.timezone:
            time_zone = account.timezone
        else:
            time_zone = account.get_timezone_from_location_zipcode()
        instance.date, instance.time = get_date_time_from_datetime_timezone(instance.scheduled_datetime,
                                                                            time_zone)
        return super().to_representation(instance)

    def get_timezone(self, instance):
        account = get_account(self.context['user'])
        if account.timezone:
            time_zone = account.timezone
        else:
            time_zone = account.get_timezone_from_location_zipcode()
        return time_zone

    def get_studentDetails(self, instance):
        if instance.student_details:
            return instance.student_details
        data = []
        if instance.booking.user.is_parent():
            if instance.booking.tied_student:
                data.append({'name': instance.booking.tied_student.name, 'age': instance.booking.tied_student.age})
        else:
            data.append({'name': instance.booking.user.first_name, 'age': instance.booking.user.student.age})
        return data


class LessonSerializer(ScheduledLessonSerializer):
    """To display info about a Lesson"""

    class Meta:
        model = Lesson
        fields = ('id', 'date', 'time', 'timezone', 'student_details', 'instructor', 'grade', 'comment')


class LessonDataSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    instructor = serializers.SerializerMethodField()
    instructorId = serializers.SerializerMethodField()
    gradeComment = serializers.CharField(source='comment')
    timezone = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'date', 'timezone', 'instructor', 'instructorId', 'status', 'grade', 'gradeComment', ]

    def get_instructor(self, instance):
        if instance.instructor:
            return instance.instructor.display_name
        elif instance.booking.instructor:
            return instance.booking.instructor.display_name
        else:
            return ''

    def get_instructorId(self, instance):
        if instance.instructor:
            return instance.instructor.id
        elif instance.booking.instructor:
            return instance.booking.instructor.id
        else:
            return None

    def get_date(self, instance):
        from lesson.utils import get_date_time_from_datetime_timezone
        account = get_account(self.context['user'])
        if account.timezone:
            time_zone = account.timezone
        else:
            time_zone = account.get_timezone_from_location_zipcode()
        if instance.scheduled_datetime:
            date, time = get_date_time_from_datetime_timezone(instance.scheduled_datetime,
                                                              time_zone,
                                                              date_format='%m/%d/%Y',
                                                              time_format='%I:%M%p')
            return f'{date} @ {time}'
        else:
            return ''

    def get_timezone(self, instance):
        account = get_account(self.context['user'])
        if account.timezone:
            time_zone = account.timezone
        else:
            time_zone = account.get_timezone_from_location_zipcode()
        return time_zone


class GetParamsInstructorMatchSerializer(serializers.ModelSerializer):
    availability = serializers.JSONField(source='trial_availability_schedule')

    class Meta:
        model = LessonRequest
        fields = ('instrument', 'availability', 'language', 'gender', 'skill_level', )


class BestInstructorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='display_name')
    reviews = serializers.SerializerMethodField()
    instruments = serializers.SerializerMethodField()
    rate = serializers.SerializerMethodField()
    lessonsTaught = serializers.IntegerField(source='lessons_taught')
    verified = serializers.SerializerMethodField()

    class Meta:
        model = Instructor
        fields = ('id', 'name', 'avatar', 'reviews', 'instruments', 'rate', 'lessonsTaught', 'verified', )

    def get_reviews(self, instance):
        reviews_data = instance.get_review_dict()
        return reviews_data

    def get_instruments(self, instance):
        popular_instruments = []
        other_instruments = []
        for instrument in instance.instruments.all():
            if instrument.name in POPULAR_INSTRUMENTS:
                popular_instruments.append(instrument.name)
            else:
                other_instruments.append(instrument.name)
        if len(popular_instruments) >= 2:
            instr_list = popular_instruments[:2]
        elif len(popular_instruments) == 1:
            instr_list = popular_instruments + other_instruments[:1]
        else:
            instr_list = other_instruments[:2]
        return instr_list

    def get_rate(self, instance):
        item = instance.instructorlessonrate_set.first()
        return item.mins30 if item else item

    def get_verified(self, instance):
        return 'Yes' if instance.bg_status == BG_STATUS_VERIFIED else 'No'


class BestInstructorMatchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='display_name')
    reviews = serializers.SerializerMethodField()
    instruments = serializers.SerializerMethodField()
    rate = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    bioTitle = serializers.SerializerMethodField()
    bioDescription = serializers.SerializerMethodField()
    yearsOfExperience = serializers.IntegerField(source='years_of_experience')
    verified = serializers.SerializerMethodField()
    tutoredStudents = serializers.SerializerMethodField()
    levelsTaught = serializers.SerializerMethodField()
    lessonsTaught = serializers.IntegerField(source='lessons_taught')

    class Meta:
        model = Instructor
        fields = ('id', 'name', 'avatar', 'reviews', 'instruments', 'rate', 'timezone',
                  'bioTitle', 'bioDescription', 'yearsOfExperience', 'verified', 'tutoredStudents', 'languages',
                  'levelsTaught', 'lessonsTaught')

    def get_reviews(self, instance):
        reviews_data = instance.get_review_dict()
        review_list = []
        for review in instance.reviews.all().order_by('-id'):
            review_list.append({'date': review.reported_at.strftime('%m/%d/%Y'), 'rating': review.rating,
                                'comment': review.comment, 'user': review.user.get_full_name()})
        if reviews_data == {}:
            reviews_data['rating'] = '0.0'
            reviews_data['quantity'] = 0
        reviews_data['items'] = review_list
        return reviews_data

    def get_instruments(self, instance):
        return [instrument.name for instrument in instance.instruments.all()]

    def get_rate(self, instance):
        item = instance.instructorlessonrate_set.first()
        return item.mins30 if item else item

    def get_timezone(self, instance):
        return instance.timezone if instance.timezone else instance.get_timezone_from_location_zipcode()

    def get_bioTitle(self, instance):
        return instance.bio_title or ''

    def get_bioDescription(self, instance):
        return instance.bio_description or ''

    def get_verified(self, instance):
        return 'Yes' if instance.bg_status == BG_STATUS_VERIFIED else 'No'

    def get_tutoredStudents(self, instance):
        set_stu = set()
        for booking in instance.bookings.all():
            if booking.lessons.filter(status=Lesson.COMPLETE).exists():
                set_stu.add(booking.student_details)
        return len(set_stu)

    def get_levelsTaught(self, instance):
        levels = {instrument.skill_level for instrument in instance.instructorinstruments_set.all()}
        return list(levels)


class InstructorMatchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='display_name')
    reviews = serializers.SerializerMethodField()
    instruments = serializers.SerializerMethodField()
    rate = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()

    class Meta:
        model = Instructor
        fields = ('id', 'name', 'avatar', 'reviews', 'instruments', 'rate', 'timezone', )

    def get_reviews(self, instance):
        reviews_data = instance.get_review_dict()
        return reviews_data

    def get_instruments(self, instance):
        return [instrument.name for instrument in instance.instruments.all()]

    def get_rate(self, instance):
        item = instance.instructorlessonrate_set.first()
        return item.mins30 if item else item

    def get_timezone(self, instance):
        return instance.timezone if instance.timezone else instance.get_timezone_from_location_zipcode()


class AssignInstructorDataSerializer(serializers.Serializer):
    requestId = serializers.IntegerField()
    instructorId = serializers.IntegerField()

    def validate_requestId(self, value):
        if not LessonBooking.objects.filter(Q(request_id=value) | Q(application__request_id=value)).exists():
            raise serializers.ValidationError(
                'There is not LessonBooking with related LessonRequest which id was provided'
            )
        else:
            return value

    def validate_instructorId(self, value):
        if not Instructor.objects.filter(id=value).exists():
            raise serializers.ValidationError('There is not Instructor with provided id')
        else:
            return value
