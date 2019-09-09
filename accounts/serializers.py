from rest_framework import serializers, validators
from django.db.models import Q
from .models import *
from lesson.models import Instrument
from .utils import *
from core.utils import *
from core.constants import GENDER_CHOICES, SKILL_LEVEL_CHOICES, DAY_CHOICES

User = get_user_model()


class BaseCreateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    middle_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    display_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    gender = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    hear_about_us = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    birthday = serializers.DateField(allow_null=True, required=True, )

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get('email')).count() > 0:
            raise validators.ValidationError('Email already registered.')
        return attrs

    def create(self, validated_data):
        user = update_model(User(), **validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        pass


class InstructorProfileSerializer(serializers.Serializer):
    bio_title = serializers.CharField(max_length=200)
    bio = serializers.CharField()
    music = serializers.CharField()

    def update(self, instance, validated_data):
        instance = update_model(instance, **validated_data)
        instance.save()
        return instance


class ParentCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Parent.objects.create(user=user, **init_kwargs(Parent(), validated_data))


class InstructorCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Instructor.objects.create(user=user, **init_kwargs(Instructor(), validated_data))


class InstructorAccountInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True, )
    last_name = serializers.CharField(required=True, )
    middle_name = serializers.CharField(required=False)
    gender = serializers.ChoiceField(required=True, choices=GENDER_CHOICES)
    phone_number = serializers.CharField(required=True, )
    location = serializers.CharField(required=True, )
    lat = serializers.CharField(max_length=50, required=True)
    lng = serializers.CharField(max_length=50, required=True)

    def update(self, instance, validated_data):
        user = instance.user
        update_model(user, **validated_data)
        user.save()
        if not self.has_number(validated_data['phone_number']):
            PhoneNumber.objects.create(user=user, phone_number=validated_data['phone_number'])
        update_model(instance, **validated_data)
        instance.save()
        return instance

    def has_number(self, number):
        return PhoneNumber.objects.filter(phone_number=number).first() is not None

    def create(self, validated_data):
        raise Exception("Create is not supposed to be called")


class InstrumentsSerializer(serializers.Serializer):
    instrument = serializers.CharField(max_length=100)
    skillLevel = serializers.ChoiceField(choices=SKILL_LEVEL_CHOICES)


class LessonSizeSerializer(serializers.Serializer):
    one_student = serializers.BooleanField()
    small_groups = serializers.BooleanField()
    large_groups = serializers.BooleanField()


class AgeGroupsSerializer(serializers.Serializer):
    children = serializers.BooleanField()
    teens = serializers.BooleanField()
    adults = serializers.BooleanField()
    seniors = serializers.BooleanField()


class LessonRateSerializer(serializers.Serializer):
    mins30 = serializers.FloatField()
    mins45 = serializers.FloatField()
    mins60 = serializers.FloatField()
    mins90 = serializers.FloatField()


class PlaceForLessonsSerializer(serializers.Serializer):
    home = serializers.BooleanField()
    studio = serializers.BooleanField()
    online = serializers.BooleanField()


class AdditionalQualifications(serializers.Serializer):
    certified_teacher = serializers.BooleanField()
    music_therapy = serializers.BooleanField()
    music_production = serializers.BooleanField()
    ear_training = serializers.BooleanField()
    conducting = serializers.BooleanField()
    virtuoso_recognition = serializers.BooleanField()
    performance = serializers.BooleanField()
    music_theory = serializers.BooleanField()
    young_children_experience = serializers.BooleanField()
    repertoire_selection = serializers.BooleanField()


class AvailavilitySerializer(serializers.Serializer):
    day_of_week = serializers.ChoiceField(choices=DAY_CHOICES)
    from1 = serializers.CharField(max_length=10)
    to = serializers.CharField(max_length=10)


class InstructorAccountStepTwoSerializer(serializers.Serializer):
    instruments = serializers.ListField(child=InstrumentsSerializer())
    lesson_size = LessonSizeSerializer()
    age_group = AgeGroupsSerializer()
    lesson_rate = LessonRateSerializer()
    place_for_lessons = PlaceForLessonsSerializer()
    availability = serializers.ListField(child=AvailavilitySerializer())
    additional_qualifications = AdditionalQualifications()

    def update(self, instance, validated_data):
        self._set_instruments(instance, validated_data['instruments'])
        self._set_lesson_size(instance, validated_data['lesson_size'])
        self._set_age_group(instance, validated_data['age_group'])
        self._set_lesson_rate(instance, validated_data['lesson_rate'])
        self._set_place_for_lessons(instance, validated_data['place_for_lessons'])
        self._set_instructor_addional_qualifications(instance, validated_data['additional_qualifications'])
        return instance

    def _set_instruments(self, instance, data):
        for item in data:
            ins = Instrument.objects.filter(name=item['instrument']).first()
            if ins is None:
                ins = Instrument.objects.create(name=item['instrument'])
            ins_ins = InstructorInstruments.objects.filter(instructor=instance, instrument=ins).first()
            if ins_ins is None:
                InstructorInstruments.objects.create(instrument=ins, instructor=instance)

    def _set_lesson_size(self, instance, data):
        self._update_or_create_model(instance=instance, model=InstructorLessonSize, data=data)

    def _set_age_group(self, instance, data):
        self._update_or_create_model(instance=instance, model=InstructorAgeGroup, data=data)

    def _set_lesson_rate(self, instance, data):
        self._update_or_create_model(instance=instance, data=data, model=InstructorLessonRate)

    def _set_place_for_lessons(self, instance, data):
        self._update_or_create_model(instance=instance, data=data, model=InstructorPlaceForLessons)

    def _set_instructor_addional_qualifications(self, instance, data):
        self._update_or_create_model(instance=instance, data=data, model=InstructorAdditionalQualifications)

    def _update_or_create_model(self, instance, data, model):
        model_instance = model.objects.filter(instructor=instance).first()
        if model_instance is None:
            data = data.copy()
            data.update({'instructor': instance})
            model_instance = model()

        update_model(model_instance, **data)
        model_instance.save()
        return model_instance

    def _set_availability(self, instance, data):
        for item in data:
            av = Availability.objects.filter(instructor=instance).filter(
                Q(from1=item['from1']) | Q(to=item['to'])).first()
            if av is None:
                av = Availability()
                av.instructor = instance

            update_model(av, item)
            av.save()
