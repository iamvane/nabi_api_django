from django.db.models import ObjectDoesNotExist

from rest_framework import serializers

from accounts.models import TiedStudent
from core.constants import (LESSON_DURATION_30, LESSON_DURATION_45, LESSON_DURATION_60, LESSON_DURATION_90,
                            PLACE_FOR_LESSONS_CHOICES, SKILL_LEVEL_CHOICES)
from lesson.models import Instrument

from .models import LessonRequest


class LessonRequestStudentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=250)
    age = serializers.IntegerField()


class LessonRequestSerializer(serializers.ModelSerializer):
    MINS30_DURATION = '30mins'
    MINS45_DURATION = '45mins'
    MINS60_DURATION = '60mins'
    MINS90_DURATION = '90mins'
    LESSON_DURATION_CHOICES = [MINS30_DURATION, MINS45_DURATION, MINS60_DURATION, MINS90_DURATION]
    instrument = serializers.CharField(max_length=250)
    lessons_duration = serializers.ChoiceField(choices=LESSON_DURATION_CHOICES)
    place_for_lessons = serializers.ChoiceField(choices=PLACE_FOR_LESSONS_CHOICES)
    skill_level = serializers.ChoiceField(choices=SKILL_LEVEL_CHOICES)
    students = serializers.ListField(child=serializers.DictField(), required=False)
    user_id = serializers.IntegerField(source='user.id')

    class Meta:
        model = LessonRequest
        fields = ('user_id', 'title', 'message', 'instrument', 'lessons_duration',
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
        if keys.get('placeForLessons'):
            new_data['place_for_lessons'] = data.get('placeForLessons')
        if keys.get('skillLevel'):
            new_data['skill_level'] = data.get('skillLevel')
        if keys.get('students'):
            new_data['students'] = data.get('students')
        return super().to_internal_value(new_data)

    def validate_instrument(self, value):
        if not Instrument.objects.filter(name=value).exists():
            raise serializers.ValidationError('Instrument value is not registered')
        else:
            return value

    def validate_students(self, value):
        ser = LessonRequestStudentCreateSerializer(data=value, many=True)
        if not ser.is_valid():
            raise serializers.ValidationError(ser.errors)
        for item in value:
            if not TiedStudent.objects.filter(name=item['name'], age=item['age']).exists():
                raise serializers.ValidationError('There are not registered student for provided data')
        return ser.validated_data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.instance:
            if self.context['is_parent'] and not attrs.get('students'):
                raise serializers.ValidationError('students data must be provided')
        return attrs

    def create(self, validated_data):
        instrument = Instrument.objects.get(name=validated_data.pop('instrument'))
        validated_data['user_id'] = validated_data.get('user', {}).get('id')
        validated_data.pop('user')
        validated_data['instrument_id'] = instrument.id
        if validated_data['lessons_duration'] == self.MINS30_DURATION:
            validated_data['lessons_duration'] = LESSON_DURATION_30
        elif validated_data['lessons_duration'] == self.MINS45_DURATION:
            validated_data['lessons_duration'] = LESSON_DURATION_45
        elif validated_data['lessons_duration'] == self.MINS60_DURATION:
            validated_data['lessons_duration'] = LESSON_DURATION_60
        else:
            validated_data['lessons_duration'] = LESSON_DURATION_90
        if self.context['is_parent']:
            students_data = validated_data.pop('students')
            res = super().create(validated_data)
            for student_item in students_data:
                tied_student = TiedStudent.objects.get(name=student_item['name'], age=student_item['age'])
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
            instrument = Instrument.objects.get(name=validated_data.pop('instrument'))
            validated_data['instrument_id'] = instrument.id
        if validated_data:
            super().update(instance, validated_data)
            instance.refresh_from_db()
        if student_data:
            if isinstance(student_data, list):
                ts_id_list = []
                for student_item in student_data:
                    if TiedStudent.objects.filter(**student_item).exists():
                        ts_id_list.append(TiedStudent.objects.get(**student_item))
                instance.students.set(ts_id_list)
            else:
                instance.students.add(TiedStudent.objects.get(name=student_data['name'], age=student_data['age']))
        return instance
