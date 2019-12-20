from django.contrib.auth import get_user_model

from rest_framework import serializers

from accounts.models import TiedStudent, get_account
from core.constants import (LESSON_DURATION_CHOICES, PLACE_FOR_LESSONS_CHOICES, ROLE_STUDENT, SKILL_LEVEL_CHOICES)
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
    instrument = serializers.CharField(max_length=250, source='instrument.name', read_only=True)
    location = serializers.CharField(max_length=150, source='*', read_only=True)
    students = LessonRequestStudentSerializer(many=True, read_only=True)

    class Meta:
        model = LessonRequest
        fields = ('avatar', 'created_at', 'id', 'instrument',  'lessons_duration', 'location', 'message',
                  'place_for_lessons', 'skill_level', 'students', 'title', )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        new_data = {}
        new_data['createdAt'] = data.get('created_at')
        new_data['id'] = data.get('id')
        new_data['instrument'] = data.get('instrument')
        new_data['lessonDuration'] = data.get('lessons_duration')
        new_data['requestMessage'] = data.get('message')
        new_data['placeForLessons'] = data.get('place_for_lessons')
        new_data['skillLevel'] = data.get('skill_level')
        new_data['requestTitle'] = data.get('title')
        role = instance.user.get_role()
        if role == ROLE_STUDENT:
            new_data['studentDetails'] = [{'name': instance.user.first_name, 'age': instance.user.student.age}]
            try:
                new_data['avatar'] = instance.user.student.avatar.path
            except ValueError:
                new_data['avatar'] = ''
            new_data['location'] = instance.user.student.location
            coords_requestor = instance.user.student.coordinates
        else:
            new_data['studentDetails'] = data.pop('students')
            try:
                new_data['avatar'] = instance.user.parent.avatar.path
            except ValueError:
                new_data['avatar'] = ''
            new_data['location'] = instance.user.parent.location
            coords_requestor = instance.user.parent.coordinates
        new_data['applicationsReceived'] = 0   # ToDo: review this
        new_data['applied'] = False   # ToDo: review this
        if coords_requestor:
            new_data['distance'] = User.objects.get(id=self.context.get('user_id'))\
                .instructor.coordinates.distance(coords_requestor)
        else:
            new_data['distance'] = None
        return new_data


class LessonRequestListQueryParamsSerializer(serializers.Serializer):
    age = serializers.IntegerField(min_value=0, max_value=120, required=False)
    distance = serializers.IntegerField(min_value=0, required=False)
    instrument = serializers.CharField(max_length=250, required=False)
    lat = serializers.FloatField(min_value=-90.00, max_value=90.00, required=False)
    lng = serializers.FloatField(min_value=-180.00, max_value=-180.00, required=False)
    place_for_lessons = serializers.ChoiceField(choices=PLACE_FOR_LESSONS_CHOICES, required=False)

    def to_internal_value(self, data):
        new_data = data.copy()
        if 'placeForLessons' in new_data.keys():
            new_data['place_for_lessons'] = new_data.pop('placeForLessons')
        return super().to_internal_value(new_data)
