from django.contrib.auth import get_user_model
from django.db.models import ObjectDoesNotExist, Q

from rest_framework import serializers, validators

from core.constants import (
    DEGREE_TYPE_CHOICES, GENDER_CHOICES, ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT, SKILL_LEVEL_CHOICES,
)
from core.utils import update_model
from lesson.models import Instrument

from .models import (
    Availability, Education, Instructor, InstructorAdditionalQualifications, InstructorAgeGroup, InstructorInstruments,
    InstructorPlaceForLessons, InstructorLessonRate, InstructorLessonSize, Parent, PhoneNumber,
    Student, StudentDetails, TiedStudent, get_account,
)
from .utils import init_kwargs

User = get_user_model()


class BaseCreateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    display_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    gender = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    birthday = serializers.DateField(allow_null=True, required=True, )
    referring_code = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=False)

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get('email')).count() > 0:
            raise validators.ValidationError('Email already registered.')
        return attrs

    def validate_referring_code(self, value):
        if value and User.get_user_from_refer_code(value) is None:
            raise validators.ValidationError('Wrong referring code value')
        else:
            return value

    def create(self, validated_data):
        ref_code = validated_data.get('referring_code')
        if ref_code:
            validated_data['referred_by'] = User.get_user_from_refer_code(ref_code)
        else:
            validated_data['referred_by'] = None
        user = update_model(User(), **validated_data)
        user.set_password(validated_data['password'])
        user.save()
        user.set_user_benefits()
        return user

    def update(self, instance, validated_data):
        pass


class UserInfoUpdateSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(max_length=30, source='first_name')
    lastName = serializers.CharField(max_length=150, source='last_name')
    middleName = serializers.CharField(max_length=50)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES)
    birthday = serializers.DateField()
    address = serializers.CharField(max_length=150)
    lat = serializers.CharField(max_length=150)
    lng = serializers.CharField(max_length=150)

    class Meta:
        model = User
        fields = ['firstName', 'lastName', 'middleName', 'email', 'gender', 'birthday', 'address', 'lat', 'lng', ]

    def update(self, instance, validated_data):
        account = get_account(instance)
        account_changed = False
        birthday = validated_data.pop('birthday', None)
        if birthday is not None:
            account.birthday = birthday
            account_changed = True
        gender = validated_data.pop('gender', None)
        if gender is not None:
            account.gender = gender
            account_changed = True
        location = validated_data.pop('address', None)
        if location is not None:
            account.location = location
            account_changed = True
        latitude = validated_data.pop('lat', None)
        if latitude is not None:
            account.lat = latitude
            account_changed = True
        longitude = validated_data.pop('lng', None)
        if longitude is not None:
            account.lng = longitude
            account_changed = True
        middle_name = validated_data.pop('middleName', None)
        if middle_name is not None:
            account.middle_name = middle_name
            account_changed = True
        if account_changed:
            account.save()
        return super().update(instance, validated_data)


class InstructorProfileSerializer(serializers.Serializer):
    bio_title = serializers.CharField(max_length=200, required=False)
    bio_description = serializers.CharField(required=False)
    music = serializers.ListField(child=serializers.CharField(), required=False)

    def update(self, instance, validated_data):
        instance = update_model(instance, **validated_data)
        instance.save()
        return instance


class ParentCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Parent.objects.create(user=user, **init_kwargs(Parent(), validated_data))


class StudentCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Student.objects.create(user=user, **init_kwargs(Student(), validated_data))


class InstructorCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Instructor.objects.create(user=user, **init_kwargs(Instructor(), validated_data))


class InstructorAccountInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True, )
    last_name = serializers.CharField(required=True, )
    middle_name = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(required=True, choices=GENDER_CHOICES)
    location = serializers.CharField(required=True, )
    lat = serializers.CharField(max_length=50, required=True)
    lng = serializers.CharField(max_length=50, required=True)

    def update(self, instance, validated_data):
        user = instance.user
        user.middle_name = validated_data['middle_name']
        update_model(user, **validated_data)
        user.save()
        update_model(instance, **validated_data)
        instance.save()
        return instance

    def has_number(self, number):
        return PhoneNumber.objects.filter(user=self, number=number).exists()

    def create(self, validated_data):
        raise Exception("Create is not supposed to be called")


class InstructorEducationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    graduationYear = serializers.IntegerField(source='graduation_year', required=True)
    degreeType = serializers.ChoiceField(source='degree_type', choices=DEGREE_TYPE_CHOICES, required=True)
    fieldOfStudy = serializers.CharField(source='field_of_study', max_length=100, required=True)
    schoolLocation = serializers.CharField(source='school_location', max_length=100, required=True)

    class Meta:
        model = Education
        fields = ['id', 'instructor', 'school', 'graduationYear', 'degreeType', 'fieldOfStudy', 'schoolLocation', ]

    def to_representation(self, instance):
        res_dict = super().to_representation(instance)
        res_dict.pop('instructor')
        return res_dict


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
    mon8to10 = serializers.BooleanField(required=False)
    mon10to12 = serializers.BooleanField(required=False)
    mon12to3 = serializers.BooleanField(required=False)
    mon3to6 = serializers.BooleanField(required=False)
    mon6to9 = serializers.BooleanField(required=False)
    tue8to10 = serializers.BooleanField(required=False)
    tue10to12 = serializers.BooleanField(required=False)
    tue12to3 = serializers.BooleanField(required=False)
    tue3to6 = serializers.BooleanField(required=False)
    tue6to9 = serializers.BooleanField(required=False)
    wed8to10 = serializers.BooleanField(required=False)
    wed10to12 = serializers.BooleanField(required=False)
    wed12to3 = serializers.BooleanField(required=False)
    wed3to6 = serializers.BooleanField(required=False)
    wed6to9 = serializers.BooleanField(required=False)
    thu8to10 = serializers.BooleanField(required=False)
    thu10to12 = serializers.BooleanField(required=False)
    thu12to3 = serializers.BooleanField(required=False)
    thu3to6 = serializers.BooleanField(required=False)
    thu6to9 = serializers.BooleanField(required=False)
    fri8to10 = serializers.BooleanField(required=False)
    fri10to12 = serializers.BooleanField(required=False)
    fri12to3 = serializers.BooleanField(required=False)
    fri3to6 = serializers.BooleanField(required=False)
    fri6to9 = serializers.BooleanField(required=False)
    sat8to10 = serializers.BooleanField(required=False)
    sat10to12 = serializers.BooleanField(required=False)
    sat12to3 = serializers.BooleanField(required=False)
    sat3to6 = serializers.BooleanField(required=False)
    sat6to9 = serializers.BooleanField(required=False)
    sun8to10 = serializers.BooleanField(required=False)
    sun10to12 = serializers.BooleanField(required=False)
    sun12to3 = serializers.BooleanField(required=False)
    sun3to6 = serializers.BooleanField(required=False)
    sun6to9 = serializers.BooleanField(required=False)


class InstructorBuildJobPreferencesSerializer(serializers.Serializer):
    instruments = serializers.ListField(child=InstrumentsSerializer())
    lesson_size = LessonSizeSerializer()
    age_group = AgeGroupsSerializer()
    lesson_rate = LessonRateSerializer()
    place_for_lessons = PlaceForLessonsSerializer()
    availability = AvailavilitySerializer()
    additional_qualifications = AdditionalQualifications()
    studio_address = serializers.CharField(max_length=200, required=False)
    travel_distance = serializers.CharField(max_length=200, required=False)
    languages = serializers.ListField(child=serializers.CharField(), required=False)

    def update(self, instance, validated_data):
        self._set_instruments(instance, validated_data['instruments'])
        self._set_lesson_size(instance, validated_data['lesson_size'])
        self._set_age_group(instance, validated_data['age_group'])
        self._set_lesson_rate(instance, validated_data['lesson_rate'])
        self._set_place_for_lessons(instance, validated_data['place_for_lessons'])
        self._set_instructor_addional_qualifications(instance, validated_data['additional_qualifications'])
        if hasattr(validated_data, 'studio_address'):
            self.studio_address = validated_data['studio_address']
        if hasattr(validated_data, 'travel_distance'):
            self.travel_distance = validated_data['travel_distance']
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


class UserEmailSerializer(serializers.Serializer):
    """Check email existence in DB. Should belong to existent user."""
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            return value
        else:
            raise validators.ValidationError("Email isn't registered")


class GuestEmailSerializer(serializers.Serializer):
    """Check email existence in DB. Shouldn't belong to existent user."""
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise validators.ValidationError("Email is registered already")
        else:
            return value


class UserPasswordSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['password', ]


class AvatarInstructorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Instructor
        fields = ['avatar', ]


class AvatarParentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['avatar', ]


class AvatarStudentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['avatar', ]


class InstrumentNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Instrument
        fields = ['name', ]


def validate_instrument(value):
    """value is instrument's name, then check to existence is done"""
    try:
        Instrument.objects.get(name=value)
    except ObjectDoesNotExist:
        raise serializers.ValidationError("Instrument value not valid")
    return value


class StudentDetailsSerializer(serializers.ModelSerializer):
    instrument = serializers.CharField(max_length=250, validators=[validate_instrument, ])   # instrument name

    class Meta:
        model = StudentDetails
        fields = ['user', 'instrument', 'skill_level', 'lesson_place', 'lesson_duration', ]

    def create(self, validated_data):
        validated_data['instrument'] = Instrument.objects.get(name=validated_data['instrument'])
        return StudentDetails.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data['instrument'] = Instrument.objects.get(name=validated_data['instrument'])
        return instance.update(**validated_data)


class TiedStudentCreateSerializer(serializers.ModelSerializer):
    """Serializer for usage with student creation by parent user."""
    name = serializers.CharField(max_length=250)
    age = serializers.IntegerField()
    instrument = serializers.CharField(max_length=250, validators=[validate_instrument, ])   # instrument name

    class Meta:
        model = StudentDetails
        fields = ['user', 'tied_student', 'name', 'age',
                  'instrument', 'skill_level', 'lesson_place', 'lesson_duration', ]

    def create(self, validated_data):
        parent = Parent.objects.get(user_id=validated_data['user'])
        tied_student = TiedStudent.objects.create(parent=parent, name=validated_data['name'], age=validated_data['age'])
        super().create({'user': validated_data['user'], 'tied_student': tied_student,
                        'instrument': Instrument.objects.get(name=validated_data['instrument']),
                        'skill_level': validated_data['skill_level'], 'lesson_place': validated_data['lesson_place'],
                        'lesson_duration': validated_data['lesson_duration']})


class TiedStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=250, source='tied_student.name')
    instrument = serializers.CharField(max_length=250, source='instrument.name')

    class Meta:
        model = StudentDetails
        fields = ['name', 'instrument', 'skill_level', 'lesson_place', 'lesson_duration', ]
