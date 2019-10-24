from django.contrib.auth import get_user_model
from django.db.models import ObjectDoesNotExist

from rest_framework import serializers, validators

from core.constants import (
    DEGREE_TYPE_CHOICES, GENDER_CHOICES, LESSON_DURATION_CHOICES, MONTH_CHOICES,
    PLACE_FOR_LESSONS_CHOICES, SKILL_LEVEL_CHOICES,
)
from core.utils import update_model
from lesson.models import Instrument

from .models import (
    Availability, Education, Employment, Instructor, InstructorAdditionalQualifications,
    InstructorAgeGroup, InstructorInstruments,
    InstructorPlaceForLessons, InstructorLessonRate, InstructorLessonSize, Parent,
    Student, StudentDetails, TiedStudent, get_account,
)
from .utils import init_kwargs

User = get_user_model()


class BaseCreateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    display_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    gender = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    birthday = serializers.DateField(allow_null=True, required=True, )   # LLL: check this
    referringCode = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=False)

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
        return data

    def to_internal_value(self, data):
        if 'displayName' in data.keys():
            data['display_name'] = data.get('displayName')
        return super().to_internal_value(data)


class UserInfoUpdateSerializer(serializers.ModelSerializer):
    middle_name = serializers.CharField(max_length=50)
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
        if latitude is not None:
            account.lat = latitude
            account_changed = True
        longitude = validated_data.pop('lng', None)
        if longitude is not None:
            account.lng = longitude
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
        return new_data


class InstructorProfileSerializer(serializers.Serializer):
    bio_title = serializers.CharField(max_length=200, required=False)
    bio_description = serializers.CharField(required=False)
    music = serializers.ListField(child=serializers.CharField(), required=False)

    def update(self, instance, validated_data):
        instance = update_model(instance, **validated_data)
        instance.save()
        return instance

    def to_internal_value(self, data):
        new_data = {
            'bio_title': data.get('bioTitle'),
            'bio_description': data.get('bioDescription'),
            'music': data.get('music'),
        }
        return super().to_internal_value(new_data)


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
        data['oneStudent'] = data['one_student']
        data['smallGroups'] = data['small_groups']
        data['largeGroups'] = data['large_groups']
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
    mins30 = serializers.FloatField()
    mins45 = serializers.FloatField()
    mins60 = serializers.FloatField()
    mins90 = serializers.FloatField()


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
        if validated_data.get('studio_address') is not None:
            self.studio_address = validated_data['studio_address']
        if validated_data.get('travel_distance') is not None:
            self.travel_distance = validated_data['travel_distance']
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


class InstructorDataSerializer(serializers.ModelSerializer):
    """Serializer for return instructor data, to usage in searching instructor"""
    display_name = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    reviews = serializers.IntegerField(default=0)
    lessons_taught = serializers.IntegerField(default=0)
    instruments = serializers.SerializerMethodField()
    last_login = serializers.DateTimeField(source='user.last_login', format='%Y-%m-%d %H:%M:%S')
    member_since = serializers.DateTimeField(source='created_at', format='%Y')

    class Meta:
        model = Instructor
        fields = ['display_name', 'avatar', 'age', 'bio_title', 'bio_description', 'location', 'reviews',
                  'instruments', 'rates', 'lessons_taught', 'last_login', 'member_since']

    def get_display_name(self, instructor):
        first_name = instructor.user.first_name
        if first_name:
            initial_last_name = instructor.user.last_name[:1]
        else:
            initial_last_name = ''
        if initial_last_name:
            return '{first_name} {initial_last_name}.'.format(first_name=first_name,
                                                              initial_last_name=initial_last_name)
        else:
            return first_name

    def get_location(self, instructor):
        return instructor.get_location()

    def get_instruments(self, instructor):
        return [item.instrument.name
                for item in instructor.instructorinstruments_set.select_related('instrument').all()]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        new_data = {'displayName': data.get('display_name'), 'age': data.get('age'),
                    'avatar': data.get('avatar').url if data.get('avatar') else data.get('avatar'),
                    'bioTitle': data.get('bio_title'), 'bioDescription': data.get('bio_description'),
                    'location': data.get('location'), 'reviews': data.get('reviews'),
                    'lessonsTaught': data.get('lessons_taught'), 'instruments': data.get('instruments'),
                    'rates': data.get('rates'), 'lastLogin': data.get('last_login'),
                    'memberSince': data.get('member_since')}
        return new_data
