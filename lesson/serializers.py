from django.contrib.auth import get_user_model

from rest_framework import serializers

from accounts.models import TiedStudent
from core.constants import LESSON_DURATION_CHOICES, PLACE_FOR_LESSONS_CHOICES, SKILL_LEVEL_CHOICES
from lesson.models import Instrument

from .models import LessonRequest

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
        fields = ('user_id', 'title', 'message', 'instrument', 'lessons_duration', 'max_travel_distance',
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
        if keys.get('maxTravelDistance'):
            new_data['max_travel_distance'] = data.get('maxTravelDistance')
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
        fields = ('id', 'instrument', 'message', 'title', 'lessons_duration', 'max_travel_distance',
                  'place_for_lessons', 'skill_level', 'students')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['lessonDuration'] = data.pop('lessons_duration')
        data['maxTravelDistance'] = data.pop('max_travel_distance')
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
