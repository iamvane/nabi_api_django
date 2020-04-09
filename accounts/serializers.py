from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import ObjectDoesNotExist

from rest_framework import serializers, validators

from core.constants import (
    DAY_TUPLE, DEGREE_TYPE_CHOICES, GENDER_CHOICES, LESSON_DURATION_CHOICES, MONTH_CHOICES,
    PLACE_FOR_LESSONS_CHOICES, SKILL_LEVEL_CHOICES,
)
from core.models import UserBenefits
from core.utils import update_model
from lesson.models import Instrument

from .models import (
    Affiliate, Availability, Education, Employment, Instructor, InstructorAdditionalQualifications,
    InstructorAgeGroup, InstructorInstruments,
    InstructorPlaceForLessons, InstructorLessonRate, InstructorLessonSize, Parent,
    Student, StudentDetails, TiedStudent, get_account,
)
from .utils import add_to_email_list, add_to_email_list_v2, init_kwargs

User = get_user_model()


class BaseCreateAccountSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    reference = serializers.CharField(max_length=200, required=False)
    email = serializers.EmailField()
    password = serializers.CharField()
    display_name = serializers.CharField(max_length=100, read_only=True)
    gender = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    birthday = serializers.DateField(allow_null=True, required=True, )   # LLL: check this
    referringCode = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=False)
    terms_accepted = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get('email')).count() > 0:
            raise validators.ValidationError('Email already registered.')
        return attrs

    def validate_referringCode(self, value):
        if value and User.get_user_from_refer_code(value) is None:
            raise validators.ValidationError('Wrong referring code value')
        else:
            return value

    def create(self, validated_data):
        ref_code = validated_data.get('referringCode')
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'display_name' in data.keys():
            data['displayName'] = data.pop('display_name')
        if 'first_name' in data.keys():
            data['firstName'] = data.pop('first_name')
        if 'last_name' in data.keys():
            data['lastName'] = data.pop('last_name')
        return data

    def to_internal_value(self, data):
        new_data = data.copy()
        keys = dict.fromkeys(data, 1)
        if keys.get('firstName'):
            new_data['first_name'] = new_data.pop('firstName')
        if keys.get('lastName'):
            new_data['last_name'] = new_data.pop('lastName')
        if keys.get('displayName'):
            new_data['display_name'] = new_data.pop('displayName')
        if keys.get('termsAccepted'):
            new_data['terms_accepted'] = new_data.pop('termsAccepted')
        return super().to_internal_value(new_data)


class UserInfoUpdateSerializer(serializers.ModelSerializer):
    middle_name = serializers.CharField(max_length=50, required=False)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES)
    location = serializers.CharField(max_length=150)
    lat = serializers.CharField(max_length=150)
    lng = serializers.CharField(max_length=150)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'middle_name', 'email', 'gender', 'location', 'lat', 'lng', ]

    def update(self, instance, validated_data):
        account = get_account(instance)
        account_changed = False
        gender = validated_data.pop('gender', None)
        if gender is not None:
            account.gender = gender
            account_changed = True
        location = validated_data.pop('location', None)
        if location is not None:
            account.location = location
            account_changed = True
        latitude = validated_data.pop('lat', None)
        longitude = validated_data.pop('lng', None)
        if latitude is not None and longitude is not None:
            point = Point(float(longitude), float(latitude))
            account.coordinates = point
            account_changed = True
        middle_name = validated_data.pop('middle_name', None)
        if middle_name is not None:
            account.middle_name = middle_name
            account_changed = True
        if account_changed:
            account.save()
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        new_data = data.copy()
        keys = dict.fromkeys(data, 1)
        if keys.get('firstName'):
            new_data['first_name'] = new_data.pop('firstName')
        if keys.get('lastName'):
            new_data['last_name'] = new_data.pop('lastName')
        if keys.get('middleName'):
            new_data['middle_name'] = new_data.pop('middleName')
        return super().to_internal_value(new_data)


class InstructorProfileSerializer(serializers.Serializer):
    bio_title = serializers.CharField(max_length=200, required=False)
    bio_description = serializers.CharField(required=False)
    music = serializers.ListField(child=serializers.CharField(), required=False)

    def update(self, instance, validated_data):
        instance = update_model(instance, **validated_data)
        instance.save()
        return instance

    def to_internal_value(self, data):
        keys = dict.fromkeys(data, 1)
        new_data = {}
        if keys.get('bioTitle'):
            new_data['bio_title'] = data.get('bioTitle')
        if keys.get('bioDescription'):
            new_data['bio_description'] = data.get('bioDescription')
        if keys.get('music'):
            new_data['music'] = data.get('music')
        return super().to_internal_value(new_data)


class ParentCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        parent = Parent.objects.create(user=user, **init_kwargs(Parent(), validated_data))
        parent.set_display_name()
        parent.set_referral_token()
        if not settings.DEBUG:
            add_to_email_list_v2(user, 'parents', 'FacebookLead')   # add to list in HubSpot
        return parent


class StudentCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        student = Student.objects.create(user=user, **init_kwargs(Student(), validated_data))
        student.set_display_name()
        student.set_referral_token()
        if not settings.DEBUG:
            add_to_email_list_v2(user, 'students', 'FacebookLead')   # add to list in HubSpot
        return student


class InstructorCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        instructor = Instructor.objects.create(user=user, **init_kwargs(Instructor(), validated_data))
        instructor.set_display_name()
        instructor.set_referral_token()
        if not settings.DEBUG:
            add_to_email_list_v2(user, 'instructors', 'FacebookLead')  # add to list in HubSpot
        return instructor


class InstructorEducationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = Education
        fields = ['id', 'instructor', 'school', 'graduation_year', 'degree_type', 'field_of_study', 'school_location', ]

    def to_representation(self, instance):
        res_dict = super().to_representation(instance)
        res_dict.pop('instructor')
        data = {'graduationYear': res_dict.pop('graduation_year'), 'degreeType': res_dict.pop('degree_type'),
                'fieldOfStudy': res_dict.pop('field_of_study'), 'schoolLocation': res_dict.pop('school_location')}
        res_dict.update(data)
        return res_dict

    def to_internal_value(self, data):
        if self.instance is None:
            new_data = {'instructor': data.get('instructor'), 'school': data.get('school'),
                        'graduation_year': data.get('graduationYear'), 'degree_type': data.get('degreeType'),
                        'field_of_study': data.get('fieldOfStudy'), 'school_location': data.get('schoolLocation')}
        else:
            new_data = {}
            keys = dict.fromkeys(data, 1)
            if keys.get('school'):
                new_data['school'] = data['school']
            if keys.get('graduationYear'):
                new_data['graduation_year'] = data['graduationYear']
            if keys.get('degreeType'):
                new_data['degree_type'] = data['degreeType']
            if keys.get('fieldOfStudy'):
                new_data['field_of_study'] = data['fieldOfStudy']
            if keys.get('schoolLocation'):
                new_data['school_location'] = data['schoolLocation']
        return super().to_internal_value(new_data)


class InstrumentsSerializer(serializers.Serializer):
    instrument = serializers.CharField(max_length=100)
    skill_level = serializers.ChoiceField(choices=SKILL_LEVEL_CHOICES)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['skillLevel'] = data.pop('skill_level')
        return data

    def to_internal_value(self, data):
        if self.instance is None:
            new_data = {'instrument': data.get('instrument'), 'skill_level': data.get('skillLevel')}
        else:
            new_data = {}
            if 'instrument' in data.keys():
                new_data['instrument'] = data['instrument']
            if 'skillLevel' in data.keys():
                new_data['skill_level'] = data['skillLevel']
        return new_data


class LessonSizeSerializer(serializers.Serializer):
    one_student = serializers.BooleanField()
    small_groups = serializers.BooleanField()
    large_groups = serializers.BooleanField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['oneStudent'] = data.pop('one_student')
        data['smallGroups'] = data.pop('small_groups')
        data['largeGroups'] = data.pop('large_groups')
        return data

    def to_internal_value(self, data):
        new_data = {}
        keys = dict.fromkeys(data, 1)
        if 'oneStudent' in keys:
            new_data['one_student'] = data['oneStudent']
        if 'smallGroups' in keys:
            new_data['small_groups'] = data['smallGroups']
        if 'largeGroups' in keys:
            new_data['large_groups'] = data['largeGroups']
        return new_data


class AgeGroupsSerializer(serializers.Serializer):
    children = serializers.BooleanField(required=False)
    teens = serializers.BooleanField(required=False)
    adults = serializers.BooleanField(required=False)
    seniors = serializers.BooleanField(required=False)


class LessonRateSerializer(serializers.Serializer):
    mins30 = serializers.DecimalField(max_digits=9, decimal_places=4)
    mins45 = serializers.DecimalField(max_digits=9, decimal_places=4)
    mins60 = serializers.DecimalField(max_digits=9, decimal_places=4)
    mins90 = serializers.DecimalField(max_digits=9, decimal_places=4)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['mins30'][-2:] == '00':
            data['mins30'] = data['mins30'][:-2]
        elif data['mins30'][-1] == '0':
            data['mins30'] = data['mins30'][:-1]
        if data['mins45'][-2:] == '00':
            data['mins45'] = data['mins45'][:-2]
        elif data['mins45'][-1] == '0':
            data['mins45'] = data['mins45'][:-1]
        if data['mins60'][-2:] == '00':
            data['mins60'] = data['mins60'][:-2]
        elif data['mins60'][-1] == '0':
            data['mins60'] = data['mins60'][:-1]
        if data['mins90'][-2:] == '00':
            data['mins90'] = data['mins90'][:-2]
        elif data['mins90'][-1] == '0':
            data['mins90'] = data['mins90'][:-1]
        return data


class PlaceForLessonsSerializer(serializers.Serializer):
    home = serializers.BooleanField(required=False)
    studio = serializers.BooleanField(required=False)
    online = serializers.BooleanField(required=False)


class AdditionalQualifications(serializers.Serializer):
    certified_teacher = serializers.BooleanField(required=False)
    music_therapy = serializers.BooleanField(required=False)
    music_production = serializers.BooleanField(required=False)
    ear_training = serializers.BooleanField(required=False)
    conducting = serializers.BooleanField(required=False)
    virtuoso_recognition = serializers.BooleanField(required=False)
    performance = serializers.BooleanField(required=False)
    music_theory = serializers.BooleanField(required=False)
    young_children_experience = serializers.BooleanField(required=False)
    repertoire_selection = serializers.BooleanField(required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        new_data = {'certifiedTeacher': data.get('certified_teacher'), 'musicTherapy': data.get('music_therapy'),
                    'musicProduction': data.get('music_production'), 'earTraining': data.get('ear_training'),
                    'conducting': data.get('conducting'), 'virtuosoRecognition': data.get('virtuoso_recognition'),
                    'performance': data.get('performance'), 'musicTheory': data.get('music_theory'),
                    'youngChildrenExperience': data.get('young_children_experience'),
                    'repertoireSelection': data.get('repertoire_selection')}
        return new_data

    def to_internal_value(self, data):
        new_data = {}
        keys = dict.fromkeys(data, 1)
        if keys.get('certifiedTeacher'):
            new_data['certified_teacher'] = data['certifiedTeacher']
        if keys.get('musicTherapy'):
            new_data['music_therapy'] = data['musicTherapy']
        if keys.get('musicProduction'):
            new_data['music_production'] = data['musicProduction']
        if keys.get('earTraining'):
            new_data['ear_training'] = data['earTraining']
        if keys.get('conducting'):
            new_data['conducting'] = data['conducting']
        if keys.get('virtuosoRecognition'):
            new_data['virtuoso_recognition'] = data['virtuosoRecognition']
        if keys.get('performance'):
            new_data['performance'] = data['performance']
        if keys.get('musicTheory'):
            new_data['music_theory'] = data['musicTheory']
        if keys.get('youngChildrenExperience'):
            new_data['young_children_experience'] = data['youngChildrenExperience']
        if keys.get('repertoireSelection'):
            new_data['repertoire_selection'] = data['repertoireSelection']
        return super().to_internal_value(new_data)


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
    instruments = serializers.ListField(child=InstrumentsSerializer(), required=False)
    lesson_size = LessonSizeSerializer(required=False)
    age_group = AgeGroupsSerializer(required=False)
    lesson_rate = LessonRateSerializer(required=False)
    place_for_lessons = PlaceForLessonsSerializer(required=False)
    availability = AvailavilitySerializer(required=False)
    additional_qualifications = AdditionalQualifications(required=False)
    studio_address = serializers.CharField(max_length=200, required=False)
    travel_distance = serializers.CharField(max_length=200, required=False)
    languages = serializers.ListField(child=serializers.CharField(), required=False)

    def to_internal_value(self, data):
        new_data = {}
        keys = dict.fromkeys(data, 1)
        if keys.get('lessonSize'):
            new_data['lesson_size'] = data.get('lessonSize')
        if keys.get('ageGroup'):
            new_data['age_group'] = data.get('ageGroup')
        if keys.get('rates'):
            new_data['lesson_rate'] = data.get('rates')
        if keys.get('placeForLessons'):
            new_data['place_for_lessons'] = data.get('placeForLessons')
        if keys.get('availability'):
            new_data['availability'] = data.get('availability')
        if keys.get('qualifications'):
            new_data['additional_qualifications'] = data.get('qualifications')
        if keys.get('languages'):
            new_data['languages'] = data.get('languages')
        if keys.get('instruments'):
            new_data['instruments'] = data.get('instruments')
        if keys.get('studioAddress'):
            new_data['studio_address'] = data.get('studioAddress')
        if keys.get('travelDistance'):
            new_data['travel_distance'] = data.get('travelDistance')
        return super().to_internal_value(new_data)

    def update(self, instance, validated_data):
        if validated_data.get('instruments') is not None:
            self._set_instruments(instance, validated_data['instruments'])
        if validated_data.get('lesson_size') is not None:
            self._set_lesson_size(instance, validated_data['lesson_size'])
        if validated_data.get('age_group') is not None:
            self._set_age_group(instance, validated_data['age_group'])
        if validated_data.get('lesson_rate') is not None:
            self._set_lesson_rate(instance, validated_data['lesson_rate'])
        if validated_data.get('place_for_lessons') is not None:
            self._set_place_for_lessons(instance, validated_data['place_for_lessons'])
        if validated_data.get('additional_qualifications') is not None:
            self._set_instructor_addional_qualifications(instance, validated_data['additional_qualifications'])
        if validated_data.get('availability') is not None:
            self._set_availability(instance, validated_data['availability'])
        changed_instance = False
        if validated_data.get('languages') is not None:
            instance.languages = validated_data['languages']
            changed_instance = True
        if validated_data.get('studio_address') is not None:
            instance.studio_address = validated_data['studio_address']
            changed_instance = True
        if validated_data.get('travel_distance') is not None:
            instance.travel_distance = validated_data['travel_distance']
            changed_instance = True
        if changed_instance:
            instance.save()
        return instance

    def _set_instruments(self, instance, data):
        InstructorInstruments.objects.filter(instructor=instance).delete()
        for item in data:
            ins = Instrument.objects.filter(name=item['instrument']).first()
            if ins is None:
                ins = Instrument.objects.create(name=item['instrument'])
            InstructorInstruments.objects.create(instrument=ins, instructor=instance, skill_level=item['skill_level'])

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
        self._update_or_create_model(instance=instance, data=data, model=Availability)


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
            raise validators.ValidationError("Email is already registered.")
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


class StudentDetailsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, source='pk')
    instrument = serializers.CharField(max_length=250, source='instrument.name')   # instrument name

    class Meta:
        model = StudentDetails
        fields = ['id', 'user', 'instrument', 'skill_level', 'lesson_place', 'lesson_duration', ]

    def create(self, validated_data):
        validated_data['instrument'], _ = Instrument.objects.get_or_create(name=validated_data['instrument']['name'])
        return StudentDetails.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('instrument') is not None:
            validated_data['instrument'], _ = Instrument.objects.get_or_create(name=validated_data['instrument']['name'])
        return instance.update(**validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('user')
        data.update({'skillLevel': data.pop('skill_level'), 'lessonPlace': data.pop('lesson_place'),
                     'lessonDuration': data.pop('lesson_duration')})
        return data

    def to_internal_value(self, data):
        new_data = {}
        keys = dict.fromkeys(data, 1)
        if keys.get('user'):
            new_data['user'] = data['user']
        if keys.get('instrument'):
            new_data['instrument'] = data['instrument']
        if keys.get('skillLevel'):
            new_data['skill_level'] = data['skillLevel']
        if keys.get('lessonPlace'):
            new_data['lesson_place'] = data['lessonPlace']
        if keys.get('lessonDuration'):
            new_data['lesson_duration'] = data['lessonDuration']
        return super().to_internal_value(new_data)


class TiedStudentSerializer(serializers.ModelSerializer):
    """Serializer for usage with detail student creation and retrieve, by parent user."""
    id = serializers.IntegerField(source='pk', read_only=True)
    name = serializers.CharField(max_length=250, source='tied_student.name')
    age = serializers.IntegerField(source='tied_student.age')
    instrument = serializers.CharField(max_length=250, source='instrument.name')   # instrument name

    class Meta:
        model = StudentDetails
        fields = ['id', 'user', 'name', 'age', 'instrument', 'skill_level', 'lesson_place', 'lesson_duration', ]

    def create(self, validated_data):
        parent = Parent.objects.get(user_id=validated_data['user'])
        tied_student = TiedStudent.objects.create(parent=parent, name=validated_data['tied_student']['name'],
                                                  age=validated_data['tied_student']['age'])
        validated_data['tied_student'] = tied_student
        validated_data['instrument'], _ = Instrument.objects.get_or_create(name=validated_data['instrument']['name'])
        return super().create(validated_data)

    def to_representation(self, instance):
        dict_data = super().to_representation(instance)
        dict_data.pop('user')
        data = {'skillLevel': dict_data.pop('skill_level'), 'lessonPlace': dict_data.pop('lesson_place'),
                'lessonDuration': dict_data.pop('lesson_duration')}
        dict_data.update(data)
        return dict_data

    def to_internal_value(self, data):
        new_data = data.copy()
        alt_data = {'skill_level': new_data.pop('skillLevel'), 'lesson_place': new_data.pop('lessonPlace'),
                    'lesson_duration': new_data.pop('lessonDuration')}
        new_data.update(alt_data)
        if self.context.get('user'):
            new_data['instructor'] = self.context['user'].instructor.pk
        return super().to_internal_value(new_data)


class TiedStudentItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    name = serializers.CharField(max_length=250, source='tied_student.name')
    age = serializers.IntegerField(source='tied_student.age')
    instrument = serializers.CharField(max_length=250, source='instrument.name')   # instrument name

    class Meta:
        model = StudentDetails
        fields = ['id', 'name', 'age', 'instrument', 'skill_level', 'lesson_place', 'lesson_duration', ]

    def update(self, instance, validated_data):
        if validated_data.get('instrument') is not None:
            validated_data['instrument'], _ = Instrument.objects.get_or_create(name=validated_data['instrument']['name'])
        if validated_data.get('tied_student') is not None:
            if validated_data['tied_student'].get('age') is not None:
                instance.tied_student.age = validated_data['tied_student']['age']
            if validated_data['tied_student'].get('name') is not None:
                instance.tied_student.name = validated_data['tied_student']['name']
            validated_data.pop('tied_student')
            instance.tied_student.save()
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        new_data = data.copy()
        keys = dict.fromkeys(data, 1)
        if keys.get('skillLevel') is not None:
            new_data['skill_level'] = data.pop('skillLevel')
        if keys.get('lessonPlace'):
            new_data['lesson_place'] = data.pop('lessonPlace')
        if keys.get('lessonDuration'):
            new_data['lesson_duration'] = data.pop('lessonDuration')
        return super().to_internal_value(new_data)


class InstructorEmploymentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, source='pk')

    class Meta:
        model = Employment
        fields = ['id', 'instructor', 'employer', 'job_title', 'job_location', 'from_month', 'from_year',
                  'to_month', 'to_year', 'still_work_here', ]

    def to_representation(self, instance):
        dict_data = super().to_representation(instance)
        dict_data.pop('instructor')
        data = {'jobTitle': dict_data.pop('job_title'), 'jobLocation': dict_data.pop('job_location'),
                'fromMonth': dict_data.pop('from_month'), 'fromYear': dict_data.pop('from_year'),
                'toMonth': dict_data.pop('to_month'), 'toYear': dict_data.pop('to_year'),
                'stillWorkHere': dict_data.pop('still_work_here')}
        dict_data.update(data)
        return dict_data

    def to_internal_value(self, data):
        if self.instance is None:
            new_data = {'employer': data.get('employer'), 'job_title': data.get('jobTitle'),
                        'job_location': data.get('jobLocation'), 'from_month': data.get('fromMonth'),
                        'from_year': data.get('fromYear'), 'to_month': data.get('toMonth'),
                        'to_year': data.get('toYear')}
            if 'stillWorkHere' in data.keys():
                new_data['still_work_here'] = data.get('stillWorkHere')
            if self.context.get('user'):
                new_data['instructor'] = self.context['user'].instructor.pk
        else:
            new_data = {}
            keys = dict.fromkeys(data, 1)
            if keys.get('employer'):
                new_data['employer'] = data['employer']
            if keys.get('jobTitle'):
                new_data['job_title'] = data['jobTitle']
            if keys.get('jobLocation'):
                new_data['job_location'] = data['jobLocation']
            if keys.get('fromMonth'):
                new_data['from_month'] = data['fromMonth']
            if keys.get('fromYear'):
                new_data['from_year'] = data['fromYear']
            if keys.get('toMonth'):
                new_data['to_month'] = data['toMonth']
            if keys.get('toYear'):
                new_data['to_year'] = data['toYear']
            if keys.get('stillWorkHere'):
                new_data['still_work_here'] = data['stillWorkHere']
        return super().to_internal_value(new_data)

    def validate(self, data):
        if self.partial:   # when update operation is requested
            still_work_here = data.get('still_work_here') if 'still_work_here' in data.keys() \
                else self.instance.still_work_here
            to_year = data.get('to_year') if 'to_year' in data.keys() else self.instance.to_year
            if to_year == '':
                to_year = None
            to_month = data.get('to_month') if 'to_month' in data.keys() else self.instance.to_month
            if to_month == '':
                to_month = None
            if still_work_here and (to_year is not None or to_month is not None):
                raise serializers.ValidationError('toYear or toMonth values are not congruent with stillWorkHere value')
            elif not still_work_here and (to_year is None or to_month is None):
                raise serializers.ValidationError('toYear or toMonth values are not congruent with stillWorkHere value')
            return data
        else:
            if 'still_work_here' in data.keys():
                still_work_here = data['still_work_here']
            else:
                still_work_here = False
            if not still_work_here:
                if not data.get('to_year') or not data.get('to_month'):
                    raise serializers.ValidationError('If you not work here currently, final date should be provided')
            if data.get('to_month') and not data.get('to_year'):
                raise serializers.ValidationError('Year of final date should be provided')
            if data.get('from_month') and not data.get('from_year'):
                raise serializers.ValidationError('Year of initial date should be provided')
            return data


class InstructorQueryParamsSerializer(serializers.Serializer):
    qualifications_dict = {'certifiedTeacher': 'certified_teacher', 'musicTherapy': 'music_therapy',
                           'musicProduction': 'music_production', 'earTraining': 'ear_training',
                           'conducting': 'conducting', 'virtuosoRecognition': 'virtuoso_recognition',
                           'performance': 'performance', 'musicTheory': 'music_theory',
                           'youngChildrenExperience': 'young_children_experience',
                           'repertoireSelection': 'repertoire_selection'}
    availability = serializers.CharField(max_length=500, required=False)
    distance = serializers.IntegerField(required=False, default=50)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False)
    instruments = serializers.CharField(max_length=500, required=False)
    languages = serializers.CharField(max_length=500, required=False)
    location = serializers.CharField(max_length=200, required=False)
    min_rate = serializers.DecimalField(max_digits=9, decimal_places=4, required=False)
    max_rate = serializers.DecimalField(max_digits=9, decimal_places=4, required=False)
    place_for_lessons = serializers.CharField(max_length=300, required=False)
    qualifications = serializers.CharField(max_length=500, required=False)
    student_ages = serializers.CharField(max_length=100, required=False)
    sort = serializers.CharField(max_length=50, required=False)

    def to_internal_value(self, data):
        keys = dict.fromkeys(data, 1)
        new_data = data.copy()
        if keys.get('placeForLessons'):
            new_data['place_for_lessons'] = new_data.pop('placeForLessons')
        if keys.get('studentAges'):
            new_data['student_ages'] = new_data.pop('studentAges')
        if keys.get('minRate'):
            new_data['min_rate'] = new_data.pop('minRate')
        if keys.get('maxRate'):
            new_data['max_rate'] = new_data.pop('maxRate')
        return super().to_internal_value(new_data)

    def validate_availability(self, value):
        if value == '':
            raise serializers.ValidationError('Wrong availability value')
        list_values = value.split(',')
        for item in list_values:
            if item not in DAY_TUPLE:
                raise serializers.ValidationError('Wrong availability value')
        return value

    def validate_place_for_lessons(self, value):
        if value == '':
            raise serializers.ValidationError('Wrong placeForLessons value')
        list_values = value.split(',')
        for item in list_values:
            if not hasattr(InstructorPlaceForLessons, item):
                raise serializers.ValidationError('Wrong placeForLessons value')
        return value

    def validate_qualifications(self, value):
        if value == '':
            raise serializers.ValidationError('Wrong qualifications value')
        list_values = value.split(',')
        new_value = ''
        for item in list_values:
            if self.qualifications_dict.get(item):
                if new_value:
                    new_value += ',' + self.qualifications_dict.get(item)
                else:
                    new_value += self.qualifications_dict.get(item)
            else:
                raise serializers.ValidationError('Wrong qualifications value')
        return new_value

    def validate_student_ages(self, value):
        if value == '':
            raise serializers.ValidationError('Wrong studentAges value')
        list_values = value.split(',')
        for item in list_values:
            if not hasattr(InstructorAgeGroup, item):
                raise serializers.ValidationError('Wrong studentAges value')
        return value

    def validate_sort(self, value):
        if value not in ('distance', '-distance', 'rate', '-rate'):
            raise serializers.ValidationError('Wrong sort value')
        else:
            return value

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


class InstructorDataSerializer(serializers.ModelSerializer):
    """Serializer for return instructor data, to usage in searching instructor"""
    availability = serializers.SerializerMethodField()
    distance = serializers.FloatField(source='distance.mi', read_only=True)
    instruments = serializers.SerializerMethodField()
    lessons_taught = serializers.IntegerField(default=0, read_only=True)
    location = serializers.SerializerMethodField()
    place_for_lessons = serializers.SerializerMethodField()
    rates = serializers.SerializerMethodField()
    qualifications = serializers.SerializerMethodField()
    student_ages = serializers.SerializerMethodField()
    reviews = serializers.IntegerField(default=0, read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', format='%Y-%m-%d %H:%M:%S', read_only=True)
    member_since = serializers.DateTimeField(source='created_at', format='%Y', read_only=True)

    class Meta:
        model = Instructor
        fields = ('id', 'display_name', 'avatar', 'age', 'gender', 'bio_title', 'bio_description', 'languages',
                  'bg_status', 'distance', 'reviews', 'location', 'interviewed', 'instruments', 'rates', 'availability',
                  'place_for_lessons', 'experience_years', 'qualifications', 'lessons_taught', 'student_ages',
                  'last_login', 'member_since')

    def get_availability(self, instructor):
        items = instructor.availability.all()
        if len(items):
            ser = AvailavilitySerializer(items[0])
            return ser.data
        else:
            return {}

    def get_location(self, instructor):
        return instructor.get_location()

    def get_instruments(self, instructor):
        return [item.instrument.name
                for item in instructor.instructorinstruments_set.select_related('instrument').all()]

    def get_rates(self, instructor):
        items = instructor.instructorlessonrate_set.all()
        if len(items):
            ser = LessonRateSerializer(items[0])
            return ser.data
        else:
            return {'mins30': '', 'mins45': '', 'mins60': '', 'mins90': ''}

    def get_place_for_lessons(self, instructor):
        items = instructor.instructorplaceforlessons_set.all()
        if len(items):
            ser = PlaceForLessonsSerializer(items[0])
            return ser.data
        else:
            return {}

    def get_qualifications(self, instructor):
        items = instructor.instructoradditionalqualifications_set.all()
        if len(items):
            ser = AdditionalQualifications(items[0])
            return ser.data
        else:
            return {}

    def get_student_ages(self, instructor):
        items = instructor.instructoragegroup_set.all()
        if len(items):
            ser = AgeGroupsSerializer(items[0])
            return ser.data
        else:
            return {}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        new_data = {'id': data.get('id'), 'displayName': data.get('display_name'), 'age': data.get('age'),
                    'avatar': data.get('avatar') if data.get('avatar') else data.get('avatar'),
                    'backgroundCheckStatus': data.get('bg_status'), 'distance': data.get('distance'),
                    'bioTitle': data.get('bio_title'), 'bioDescription': data.get('bio_description'),
                    'gender': data.get('gender'), 'reviews': data.get('reviews'), 'location': data.get('location'),
                    'qualifications': data.get('qualifications'), 'interviewed': data.get('interviewed'),
                    'lessonsTaught': data.get('lessons_taught'), 'instruments': data.get('instruments'),
                    'rates': data.get('rates'), 'placeForLessons': data.get('place_for_lessons'),
                    'availability': data.get('availability'), 'student_ages': data.get('student_ages'),
                    'languages': data.get('languages'), 'yearsOfExperience': data.get('experience_years'),
                    'lastLogin': data.get('last_login'), 'memberSince': data.get('member_since')}
        return new_data


class InstructorInstrumentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='instrument.name')

    class Meta:
        model = InstructorInstruments
        fields = ['name', 'skill_level']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['skillLevel'] = data.pop('skill_level')
        return data


class InstructorDetailSerializer(serializers.ModelSerializer):
    """Serializer to get data of an instructor"""
    distance = serializers.SerializerMethodField()
    instruments = InstructorInstrumentSerializer(source='instructorinstruments_set', many=True, read_only=True)
    lesson_size = LessonSizeSerializer(source='instructorlessonsize_set', many=True, read_only=True)
    age_group = AgeGroupsSerializer(source='instructoragegroup_set', many=True, read_only=True)
    rates = LessonRateSerializer(source='instructorlessonrate_set', many=True, read_only=True)
    place_for_lessons = PlaceForLessonsSerializer(source='instructorplaceforlessons_set', many=True, read_only=True)
    availability = AvailavilitySerializer(many=True, read_only=True)
    qualifications = AdditionalQualifications(source='instructoradditionalqualifications_set', many=True, read_only=True)
    languages = serializers.ListField(child=serializers.CharField(), read_only=True)
    lessons_taught = serializers.IntegerField(default=0)
    education = InstructorEducationSerializer(many=True, read_only=True)
    employment = InstructorEmploymentSerializer(many=True, read_only=True)
    reviews = serializers.IntegerField(default=0)
    member_since = serializers.DateTimeField(source='created_at', format='%Y')

    class Meta:
        model = Instructor
        fields = ['id', 'user_id', 'display_name', 'age', 'member_since', 'bg_status', 'bio_title', 'bio_description',
                  'interviewed', 'location', 'distance', 'music', 'instruments', 'lesson_size', 'age_group', 'rates',
                  'place_for_lessons', 'availability', 'reviews', 'qualifications', 'languages', 'studio_address',
                  'travel_distance', 'lessons_taught', 'education', 'employment', 'experience_years', 'avatar']

    def get_distance(self, instance):
        if self.context.get('account') and self.context.get('account').coordinates:
            coords = self.context.get('account').coordinates
        else:
            coords = None
        if instance.coordinates and coords:
            return instance.coordinates.distance(coords) * 100 * 0.62137119223733
        else:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['userId'] = data.pop('user_id')
        data['displayName'] = data.pop('display_name')
        data['backgroundCheckStatus'] = data.pop('bg_status')
        data['bioTitle'] = data.pop('bio_title')
        data['bioDescription'] = data.pop('bio_description')
        data['studioAddress'] = data.pop('studio_address')
        data['travelDistance'] = data.pop('travel_distance')
        data['memberSince'] = data.pop('member_since')
        data['yearsOfExperience'] = data.pop('experience_years')
        data['avatar'] = data.pop('avatar')
        if data.get('lesson_size'):
            data['lessonSize'] = data.pop('lesson_size')[0]
        else:
            data['lessonSize'] = data.pop('lesson_size')
        if data.get('age_group'):
            data['ageGroup'] = data.pop('age_group')[0]
        else:
            data['ageGroup'] = data.pop('age_group')
        if data.get('place_for_lessons'):
            data['placeForLessons'] = data.pop('place_for_lessons')[0]
        else:
            data['placeForLessons'] = data.pop('place_for_lessons')
        data['lessonsTaught'] = data.pop('lessons_taught')
        if data.get('availability'):
            data['availability'] = data.pop('availability')[0]
        if data.get('rates'):
            rates = data.pop('rates')[0]
            data['rates'] = {'mins30': str(rates['mins30']), 'mins45': str(rates['mins45']),
                             'mins60': str(rates['mins60']), 'mins90': str(rates['mins90'])}
        else:
            data['rates'] = {'mins30': '', 'mins45': '', 'mins60': '', 'mins90': ''}
        if data.get('qualifications'):
            data['qualifications'] = data.pop('qualifications')[0]
        else:
            data['qualifications'] = None
        return data


class AffiliateRegisterSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    birthday = serializers.DateField(source='affiliate.birth_date')
    companyName = serializers.CharField(max_length=200, source='affiliate.company_name', required=False)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'birthday', 'companyName')
        extra_kwargs = {'password': {'write_only': True}}

    def to_internal_value(self, data):
        keys = dict.fromkeys(data)
        if 'firstName' in keys:
            data['first_name'] = data.pop('firstName')
        if 'lastName' in keys:
            data['last_name'] = data.pop('lastName')
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = data.get('id')
        data['firstName'] = data.get('first_name')
        data['lastName'] = data.get('last_name')
        return data

    def create(self, validated_data):
        user = User.objects.create(first_name=validated_data.get('first_name', ''),
                                   last_name=validated_data.get('last_name', ''),
                                   email=validated_data['email'])
        user.set_password(validated_data['password'])
        user.save()
        affiliate = Affiliate.objects.create(user=user,
                                             birth_date=validated_data.get('affiliate', {}).get('birth_date'),
                                             company_name=validated_data.get('affiliate', {}).get('company_name', ''))
        affiliate.set_referrral_token()
        user.refresh_from_db()
        return user


class ReferralDashboardSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=9, decimal_places=4, source='benefit_qty')
    date = serializers.DateTimeField(source='modified_at', format='%Y-%m-%d')

    class Meta:
        model = UserBenefits
        fields = ('name', 'amount', 'date', 'source', )

    def get_name(self, instance):
        account = get_account(instance.provider)
        return account.display_name
