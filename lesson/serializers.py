from django.contrib.auth import get_user_model

from rest_framework import serializers

from accounts.models import TiedStudent, get_account
from core.constants import *
from lesson.models import Instrument

from .models import Application, LessonRequest

User = get_user_model()


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

    class Meta:
        model = LessonRequest
        fields = ('user_id', 'title', 'message', 'instrument', 'lessons_duration', 'travel_distance',
                  'place_for_lessons', 'skill_level', 'students')

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
        return super().to_internal_value(new_data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.instance:
            if self.context['is_parent'] and not attrs.get('students'):
                raise serializers.ValidationError('students data must be provided')
            if attrs['place_for_lessons'] == 'studio' and not attrs.get('travel_distance'):
                raise serializers.ValidationError('travel_distance value must be provided')
        else:
            if attrs.get('place_for_lessons') == 'studio' and (
                    (self.instance.travel_distance is None and attrs.get('travel_distance') is None)
                    or (self.instance.travel_distance is not None and 'travel_distance' in attrs.keys()
                        and attrs.get('travel_distance') is None)
            ):
                raise serializers.ValidationError('travel_distance value must be provided')
        return attrs

    def create(self, validated_data):
        instrument, _ = Instrument.objects.get_or_create(name=validated_data.pop('instrument'))
        validated_data['user_id'] = validated_data.get('user', {}).get('id')
        validated_data.pop('user')
        validated_data['instrument_id'] = instrument.id
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
        if student_data:
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
    """Serializer for fetching only"""
    instrument = serializers.CharField(read_only=True, source='instrument.name')
    students = LessonRequestStudentSerializer(many=True, read_only=True)

    class Meta:
        model = LessonRequest
        fields = ('id', 'instrument', 'message', 'title', 'lessons_duration', 'travel_distance',
                  'place_for_lessons', 'skill_level', 'students')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['lessonDuration'] = data.pop('lessons_duration')
        if data.get('travel_distance') is not None:
            data['travelDistance'] = data.pop('travel_distance')
        else:
            data.pop('travel_distance')
        data['placeForLessons'] = data.pop('place_for_lessons')
        data['skillLevel'] = data.pop('skill_level')
        data['requestTitle'] = data.pop('title')
        data['requestMessage'] = data.pop('message')
        if instance.students.count() == 0:
            data.pop('students')
            data['studentDetails'] = [{'name': instance.user.first_name, 'age': instance.user.student.age}]
        else:
            data['studentDetails'] = data.pop('students')
        return data


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
    display_name = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)
    request_id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=100, source='request.title', read_only=True)
    date_applied = serializers.DateTimeField(format='%Y-%m-%d', source='created_at')

    class Meta:
        model = Application
        fields = ('display_name', 'id', 'request_id', 'status', 'title', 'date_applied')

    def get_display_name(self, instance):
        account = get_account(instance.request.user)
        return account.display_name

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['displayName'] = data.pop('display_name')
        data['requestId'] = data.pop('request_id')
        data['dateApplied'] = data.pop('date_applied')
        return data


class LessonRequestItemSerializer(serializers.ModelSerializer):
    """Serializer for get data of a lesson request; call made by an instructor"""
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

    class Meta:
        model = LessonRequest
        fields = ('avatar', 'created_at', 'display_name', 'distance', 'id', 'instrument',  'lessons_duration',
                  'location', 'message', 'place_for_lessons', 'role', 'skill_level', 'students', 'title',
                  'applications_received', 'applied')

    def get_applications_received(self, instance):
        return instance.applications.count()

    def get_applied(self, instance):
        if self.context.get('user_id'):
            user = User.objects.get(id=self.context['user_id'])
            return instance.applications.filter(instructor=user.instructor).exists()
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
                new_data['avatar'] = instance.user.student.avatar.path
            except ValueError:
                new_data['avatar'] = ''
            new_data['location'] = instance.user.student.location
        else:
            new_data['studentDetails'] = data.get('students')
            try:
                new_data['avatar'] = instance.user.parent.avatar.path
            except ValueError:
                new_data['avatar'] = ''
            new_data['location'] = instance.user.parent.location
        return new_data


class LessonRequestListQueryParamsSerializer(serializers.Serializer):
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

    class Meta:
        model = LessonRequest
        fields = ('id', 'avatar', 'displayName', 'instrument',  'lessonDuration', 'location',
                  'requestMessage', 'placeForLessons', 'skillLevel', 'studentDetails', 'requestTitle', 'application')

    def get_avatar(self, instance):
        account = get_account(instance.user)
        if account and account.avatar:
            return account.avatar.path
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

    def get_displayName(self, instance):
        account = get_account(instance.user)
        if account:
            return account.display_name
        else:
            return ''

    def get_location(self, instance):
        account = get_account(instance.user)
        if account:
            _, state, city = account.get_location(result_type='tuple')
            return '{}, {}'.format(city, state)
        else:
            return ''

    def get_studentDetails(self, instance):
        if instance.user.is_parent():
            student_list = []
            for student in instance.students.all():
                student_list.append({'name': student.name, 'age': student.age})
            return student_list
        else:
            return [{'name': instance.user.first_name, 'age': instance.user.student.age}]

