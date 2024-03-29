from functools import reduce
from logging import getLogger
from twilio.rest import Client

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.db.models import PointField
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import transaction
from django.db.models import Min, ObjectDoesNotExist, Prefetch, Q, Sum
from django.db.models.functions import Cast
from django.middleware.csrf import get_token
from django.utils import timezone

from rest_framework import status, views
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.constants import *
from core.models import TaskLog, UserBenefits, UserToken
from core.utils import build_error_dict, generate_token_reset_password
from lesson.models import Instrument, Lesson
from lesson.serializers import BestInstructorMatchSerializer, InstructorDashboardSerializer, ScheduledLessonSerializer

from . import serializers as sers
from .models import (Availability, Education, Employment, Instructor, InstructorAgeGroup, InstructorInstruments,
                     InstructorLessonRate, InstructorPlaceForLessons, InstructorAdditionalQualifications,
                     PhoneNumber, StudentDetails, TiedStudent, get_account, get_user_phone)
from .tasks import info_instructor_review
from .utils import send_referral_invitation_email, send_reset_password_email

User = get_user_model()
logger = getLogger('api_errors')


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_user_response(account):
    user = account.user
    if account.coordinates:
        lng = str(account.coordinates.coords[0])
        lat = str(account.coordinates.coords[1])
    else:
        lat = lng = ''
    data = {
        'id': user.id,
        'email': user.email,
        'role': user.get_role(),
        'firstName': user.first_name,
        'middleName': account.middle_name,
        'lastName': user.last_name,
        'birthday': account.birthday,
        'phone': get_user_phone(account),
        'gender': account.gender,
        'location': account.location,
        'lat': lat,
        'lng': lng,
        'timezone': account.timezone,
        'referralToken': user.referral_token,
    }
    return data


def get_instructor_profile(user_cc):
    if user_cc.user.get_role() == ROLE_INSTRUCTOR:
        return {
            'bioTitle': user_cc.bio_title,
            'bioDescription': user_cc.bio_description,
            'music': user_cc.music,
            'backgroundCheckStatus': user_cc.bg_status,
            'video': user_cc.video,
            'yearsOfExperience': user_cc.years_of_experience,
        }
    else:
        return {}


class CreateAccount(views.APIView):
    permission_classes = ()

    @transaction.atomic()
    def post(self, request):
        if 'role' not in request.data:
            return Response({'detail': 'Role is required'}, status=status.HTTP_400_BAD_REQUEST)
        account_serializer = self.get_serializer_class(request)
        if account_serializer is None:
            return Response({'detail': 'Provided role is not valid'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = account_serializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            user_response = get_user_response(account)
            user_response['token'] = get_tokens_for_user(account.user)
            return Response(user_response)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self, request):
        if request.data['role'] == 'parent':
            return sers.ParentCreateAccountSerializer
        elif request.data['role'] == 'instructor':
            return sers.InstructorCreateAccountSerializer
        elif request.data['role'] == 'student':
            return sers.StudentCreateAccountSerializer


class LoginView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        form = AuthenticationForm(data={
            'username': request.data.get('email'),
            'password': request.data.get('password'),
        })
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            login(request, user)
            return Response(get_user_response(get_account(user)))
        else:
            result = build_error_dict(form.errors)
            if result.get('detail') == "Please enter a correct email address and password. Note that both fields may be case-sensitive.":
                result['message'] = result.pop('detail')
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(views.APIView):
    """For set a new password, when user forgot it."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = sers.UserEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.data['email']
            user = User.objects.get(email=email)
            token = generate_token_reset_password(user)
            if not send_reset_password_email(email, token):
                return Response({'message': "Error sending email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'message': 'Check your email to set a new password.'})
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        serializer = sers.UserPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = request.query_params.get('token')
            if token:
                try:
                    user_token = UserToken.objects.get(token=token)
                except ObjectDoesNotExist:
                    return Response({'detail': 'Wrong token value'}, status=status.HTTP_400_BAD_REQUEST)
                if user_token.expired_at < timezone.now():
                    return Response({'detail': 'Wrong token value'}, status=status.HTTP_400_BAD_REQUEST)
                passw = serializer.data['password']
                user_token.user.set_password(passw)
                user_token.user.save()
                user_token.delete()
                return Response({'message': 'Password set successfully. Please log in.'})
            else:
                return Response({'detail': 'Token value is missing'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(views.APIView):
    def get(self, request):
        logout(request)
        return Response({'message': "You have successfully logged out."})


class CsrfTokenView(views.APIView):
    def get(self, request):
        return Response({'token': get_token(request)})


class WhoAmIView(views.APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return {'id': None, 'email': None, 'role': None, 'firstName': None, 'middleName': None, 'lastName': None,
                    'birthday': None, 'phone': None, 'gender': None, 'location': None, 'lat': None, 'lng': None,
                    'referralToken': None,
                    }

        account = get_account(request.user)
        if account.coordinates:
            lng = str(account.coordinates.coords[0])
            lat = str(account.coordinates.coords[1])
        else:
            lat = lng = ''
        avatar_path = None
        if account.avatar:
            avatar_path = account.avatar.url
        if account.timezone:
            time_zone = account.timezone
        else:
            time_zone = account.get_timezone_from_location_zipcode()
        data = {
            'id': request.user.id,
            'email': request.user.email,
            'role': request.user.get_role(),
            'firstName': request.user.first_name,
            'middleName': account.middle_name,
            'lastName': request.user.last_name,
            'displayName': account.display_name,
            'birthday': account.birthday,
            'phone': get_user_phone(account),
            'gender': account.gender,
            'location': account.location,
            'timezone': time_zone,
            'lat': lat,
            'lng': lng,
            'referralToken': request.user.referral_token,
            'avatar': avatar_path
        }

        if data['role'] == ROLE_INSTRUCTOR:
            instructor = Instructor.objects.filter(user_id=data['id']).prefetch_related(
                Prefetch('instructorlessonsize_set', to_attr='lessonsizes'),
                Prefetch('instructorinstruments_set'),
                Prefetch('instructoragegroup_set', to_attr='agegroups'),
                Prefetch('instructorlessonrate_set', to_attr='lessonrates'),
                Prefetch('instructorplaceforlessons_set', to_attr='placeforlessons'),
                Prefetch('availability'),
                Prefetch('instructoradditionalqualifications_set', to_attr='additionalqualifications'),
                Prefetch('employment', ),
                Prefetch('education'),
            ).first()
            data['backgroundCheckStatus'] = account.bg_status
            data['bioTitle'] = account.bio_title
            data['instructorId'] = account.id
            data['bioDescription'] = account.bio_description
            data['music'] = account.music
            data['lessonSize'] = {'oneStudent': instructor.lessonsizes[0].one_student,
                                  'smallGroups': instructor.lessonsizes[0].small_groups,
                                  'largeGroups': instructor.lessonsizes[0].large_groups} \
                if len(instructor.lessonsizes) else {}
            data['instruments'] = [{'instrument': item.instrument.name, 'skillLevel': item.skill_level}
                                   for item in instructor.instructorinstruments_set.all()]
            data['ageGroup'] = {'children': instructor.agegroups[0].children, 'teens': instructor.agegroups[0].teens,
                                'adults': instructor.agegroups[0].adults, 'seniors': instructor.agegroups[0].seniors} \
                if len(instructor.agegroups) else {}
            data['lessonRate'] = {'mins30': instructor.lessonrates[0].mins30,
                                  'mins45': instructor.lessonrates[0].mins45,
                                  'mins60': instructor.lessonrates[0].mins60,
                                  'mins90': instructor.lessonrates[0].mins90} if len(instructor.lessonrates) else {}
            data['placeForLessons'] = {'home': instructor.placeforlessons[0].home,
                                       'studio': instructor.placeforlessons[0].studio,
                                       'online': instructor.placeforlessons[0].online} \
                if len(instructor.placeforlessons) else {}
            data['availability'] = {'mon8to10': instructor.availability.mon8to10,
                                    'mon10to12': instructor.availability.mon10to12,
                                    'mon12to3': instructor.availability.mon12to3,
                                    'mon3to6': instructor.availability.mon3to6,
                                    'mon6to9': instructor.availability.mon6to9,
                                    'tue8to10': instructor.availability.tue8to10,
                                    'tue10to12': instructor.availability.tue10to12,
                                    'tue12to3': instructor.availability.tue12to3,
                                    'tue3to6': instructor.availability.tue3to6,
                                    'tue6to9': instructor.availability.tue6to9,
                                    'wed8to10': instructor.availability.wed8to10,
                                    'wed10to12': instructor.availability.wed10to12,
                                    'wed12to3': instructor.availability.wed12to3,
                                    'wed3to6': instructor.availability.wed3to6,
                                    'wed6to9': instructor.availability.wed6to9,
                                    'thu8to10': instructor.availability.thu8to10,
                                    'thu10to12': instructor.availability.thu10to12,
                                    'thu12to3': instructor.availability.thu12to3,
                                    'thu3to6': instructor.availability.thu3to6,
                                    'thu6to9': instructor.availability.thu6to9,
                                    'fri8to10': instructor.availability.fri8to10,
                                    'fri10to12': instructor.availability.fri10to12,
                                    'fri12to3': instructor.availability.fri12to3,
                                    'fri3to6': instructor.availability.fri3to6,
                                    'fri6to9': instructor.availability.fri6to9,
                                    'sat8to10': instructor.availability.sat8to10,
                                    'sat10to12': instructor.availability.sat10to12,
                                    'sat12to3': instructor.availability.sat12to3,
                                    'sat3to6': instructor.availability.sat3to6,
                                    'sat6to9': instructor.availability.sat6to9,
                                    'sun8to10': instructor.availability.sun8to10,
                                    'sun10to12': instructor.availability.sun10to12,
                                    'sun12to3': instructor.availability.sun12to3,
                                    'sun3to6': instructor.availability.sun3to6,
                                    'sun6to9': instructor.availability.sun6to9} \
                if hasattr(instructor, 'availability') else {}
            data['qualifications'] = {'certifiedTeacher': instructor.additionalqualifications[0].certified_teacher,
                                      'musicTherapy': instructor.additionalqualifications[0].music_therapy,
                                      'musicProduction': instructor.additionalqualifications[0].music_production,
                                      'earTraining': instructor.additionalqualifications[0].ear_training,
                                      'conducting': instructor.additionalqualifications[0].conducting,
                                      'virtuosoRecognition': instructor.additionalqualifications[
                                          0].virtuoso_recognition,
                                      'performance': instructor.additionalqualifications[0].performance,
                                      'musicTheory': instructor.additionalqualifications[0].music_theory,
                                      'youngChildrenExperience': instructor.additionalqualifications[
                                          0].young_children_experience,
                                      'repertoireSelection': instructor.additionalqualifications[
                                          0].repertoire_selection} \
                if len(instructor.additionalqualifications) else {}
            data['studioAddress'] = instructor.studio_address
            data['travelDistance'] = instructor.travel_distance
            data['languages'] = instructor.languages
            data['employment'] = [{'employer': item.employer, 'jobTitle': item.job_title,
                                   'jobLocation': item.job_location, 'fromMonth': item.from_month,
                                   'fromYear': item.from_year, 'toMonth': item.to_month, 'toYear': item.to_year,
                                   'stillWorkHere': item.still_work_here}
                                  for item in instructor.employment.all()]
            data['education'] = [{'degreeType': item.degree_type, 'fieldOfStudy': item.field_of_study}
                                 for item in instructor.education.all()]
            return Response(data)
        elif data['role'] == ROLE_STUDENT:
            student = StudentDetails.objects.filter(user_id=data['id']).prefetch_related().first()
            if student:
                data['skillLevel'] = student.skill_level
                data['lessonPlace'] = student.lesson_place
                data['lessonDuration'] = student.lesson_duration
                data['instrument'] = Instrument.objects.filter(id=student.instrument_id).first().name
            return Response(data)

        else:
            students = StudentDetails.objects.filter(user_id=data['id']).prefetch_related().all()
            data['students'] = [{
                                    'name': TiedStudent.objects.filter(
                                        id=item.tied_student_id).first().name,
                                    'age': TiedStudent.objects.filter(
                                        id=item.tied_student_id).first().age,
                                    'instrument': Instrument.objects.filter(
                                        id=item.instrument_id).first().name,
                                    'skillLevel': item.skill_level,
                                    'lessonPlace': item.lesson_place,
                                    'lessonDuration': item.lesson_duration
                                } for item in students]
            return Response(data)


class FetchInstructor(views.APIView):
    def get(self, request):
        data = {}
        if request.user.is_authenticated:
            data = get_instructor_profile(get_account(request.user))
        if data:
            return Response(data)
        else:
            return Response({'message': 'You must be logged in, and be an instructor'},
                            status=status.HTTP_400_BAD_REQUEST)


class UpdateProfileView(views.APIView):
    def put(self, request):
        serializer = sers.InstructorProfileSerializer(data=request.data,
                                                      instance=Instructor.objects.get(user=request.user),
                                                      partial=True)
        if serializer.is_valid():
            serializer.save()
            ser = sers.InstructorProfileSerializer(Instructor.objects.get(user=request.user))
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class UpdateUserInfoView(views.APIView):
    def put(self, request):
        serializer = sers.UserInfoUpdateSerializer(instance=request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            ser = sers.UserInfoUpdateSerializer(request.user)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneView(views.APIView):
    def post(self, request):
        try:
            phone = PhoneNumber.objects.get(user=request.user, number=request.data['phoneNumber'])
        except ObjectDoesNotExist:
            if PhoneNumber.objects.filter(user=request.user).exists():
                PhoneNumber.objects.filter(user=request.user).update(number=request.data['phoneNumber'], verified_at=None)
                phone = PhoneNumber.objects.filter(user=request.user, number=request.data['phoneNumber']).last()
            else:
                phone = PhoneNumber.objects.create(user=request.user, number=request.data['phoneNumber'],
                                                   type=PHONE_TYPE_MAIN)
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification = client.verify \
            .services(settings.TWILIO_SERVICE_SID) \
            .verifications \
            .create(to=phone.number, channel=request.data['channel'])
        return Response({"sid": verification.sid, "status": verification.status,
                         "phoneId": phone.id, "phoneNumber": phone.number,
                         'message': 'Token was sent to {}.'.format(request.data['phoneNumber'])})

    def put(self, request):
        phone = PhoneNumber.objects.get(user=request.user, number=request.data['phoneNumber'])
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification_check = client.verify \
            .services(settings.TWILIO_SERVICE_SID) \
            .verification_checks \
            .create(to=phone.number, code=request.data['code'])
        approved = verification_check.status == 'approved'
        if approved:
            phone.verified_at = timezone.now()
            phone.save()
            return Response({'status': verification_check.status, "phoneId": phone.id, "phoneNumber": phone.number})
        else:
            return Response({'message': f'Failed phone validation ({phone.number}).'},
                            status=status.HTTP_400_BAD_REQUEST)


class InstructorBuildJobPreferences(views.APIView):
    def post(self, request):
        serializer = sers.InstructorBuildJobPreferencesSerializer(data=request.data,
                                                                  instance=Instructor.objects.get(user=request.user))
        if serializer.is_valid():
            serializer.save()
            return Response(request.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class InstructorEducationView(views.APIView):
    def post(self, request):
        data = request.data.copy()
        data['instructor'] = request.user.instructor.pk
        serializer = sers.InstructorEducationSerializer(data=data)
        if serializer.is_valid():
            obj = serializer.save()
            ser = sers.InstructorEducationSerializer(obj)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        if hasattr(request.user.instructor, 'education'):
            serializer = sers.InstructorEducationSerializer(request.user.instructor.education, many=True)
            return Response(serializer.data)
        else:
            return Response([])


class InstructorEducationItemView(views.APIView):
    def put(self, request, pk):
        data = request.data.copy()
        data['instructor'] = request.user.instructor.pk
        try:
            educ_instance = Education.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"detail": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = sers.InstructorEducationSerializer(instance=educ_instance, data=data, partial=True)
        if serializer.is_valid():
            obj = serializer.save()
            ser = sers.InstructorEducationSerializer(obj)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            educ_instance = Education.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"detail": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        ser = sers.InstructorEducationSerializer(educ_instance)
        data = ser.data
        educ_instance.delete()
        return Response(data)


class InstructorDetailView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request, pk):
        try:
            instructor = Instructor.objects.get(pk=pk)
        except Instructor.DoesNotExist:
            return Response({'detail': 'There is not instructor with provider id'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = BestInstructorMatchSerializer(instructor)
        return Response(serializer.data)


class UploadAvatarView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request):
        serializer_class = self.get_serializer_class(request)
        account = get_account(request.user)
        serializer = serializer_class(instance=account, data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            ser = serializer_class(obj)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self, request):
        role = request.user.get_role()
        if role == 'instructor':
            return sers.AvatarInstructorSerializer
        elif role == 'parent':
            return sers.AvatarParentSerializer
        else:
            return sers.AvatarStudentSerializer


class ReferralInvitation(views.APIView):
    def post(self, request):
        serializer = sers.GuestEmailSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            email = request.data['email']
            if send_referral_invitation_email(user, email):
                return Response({"message": 'Invitation sent successfully.'})
            else:
                return Response({"message": 'Email could not be send.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class StudentDetailView(views.APIView):
    def put(self, request):
        data = request.data.copy()
        data['user'] = request.user.pk
        if request.user.student_details.count():
            serializer = sers.StudentDetailsSerializer(instance=request.user.student_details,
                                                       data=data, partial=True)
        else:
            serializer = sers.StudentDetailsSerializer(data=data)
        if serializer.is_valid():
            if request.user.student_details.count():
                serializer.save()
            else:
                serializer.create(serializer.validated_data)
            ser = sers.StudentDetailsSerializer(request.user.student_details.fist())
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        if request.user.student_details.count():
            serializer = sers.StudentDetailsSerializer(request.user.student_details.first())
            return Response(serializer.data)
        else:
            return Response({})


class StudentView(views.APIView):
    def post(self, request):
        # add user's id to received data
        data = request.data.copy()
        data.update({'user': request.user.pk})
        serializer = sers.StudentSerializer(data=data)
        if serializer.is_valid():
            student_details = serializer.save()
            ser = sers.StudentSerializer(student_details)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        serializer = sers.StudentSerializer(StudentDetails.objects.filter(user__id=request.user.pk), many=True)
        return Response(serializer.data)


class TiedStudentItemView(views.APIView):
    def put(self, request, pk):
        try:
            instance = StudentDetails.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"detail": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = sers.TiedStudentItemSerializer(instance=instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            instance = StudentDetails.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"detail": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        ser = sers.TiedStudentItemSerializer(instance)
        data = ser.data
        instance.tied_student.delete()
        instance.delete()
        return Response(data)


class InstructorEmploymentView(views.APIView):
    def post(self, request):
        serializer = sers.InstructorEmploymentSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            obj = serializer.save()
            ser = sers.InstructorEmploymentSerializer(obj)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        if hasattr(request.user.instructor, 'employment'):
            serializer = sers.InstructorEmploymentSerializer(request.user.instructor.employment, many=True)
            return Response(serializer.data)
        else:
            return Response([])


class InstructorEmploymentItemView(views.APIView):
    def put(self, request, pk):
        try:
            instance = Employment.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"detail": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = sers.InstructorEmploymentSerializer(instance=instance, data=request.data,
                                                         context={'user': request.user}, partial=True)
        if serializer.is_valid():
            obj = serializer.save()
            ser = sers.InstructorEmploymentSerializer(obj)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            instance = Employment.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"detail": "Does not exist an object with provided id"},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.InstructorEmploymentSerializer(instance)
        data = ser.data
        instance.delete()
        return Response(data)


class InstructorListView(views.APIView):
    permission_classes = (AllowAny, )

    def get(self, request):
        qs = Instructor.objects.filter(complete__isnull=False)
        # adjust qs for each received param
        query_serializer = sers.InstructorQueryParamsSerializer(data=request.query_params.dict())
        if query_serializer.is_valid():
            keys = dict.fromkeys(query_serializer.validated_data, 1)
            if keys.get('availability'):
                exp_dic = {DAY_MONDAY: (Q(mon8to10=True) | Q(mon10to12=True) | Q(mon12to3=True)
                                        | Q(mon3to6=True) | Q(mon6to9=True)),
                           DAY_TUESDAY: (Q(tue8to10=True) | Q(tue10to12=True) | Q(tue12to3=True)
                                         | Q(tue3to6=True) | Q(tue6to9=True)),
                           DAY_WEDNESDAY: (Q(wed8to10=True) | Q(wed10to12=True) | Q(wed12to3=True)
                                           | Q(wed3to6=True) | Q(wed6to9=True)),
                           DAY_THURSDAY: (Q(thu8to10=True) | Q(thu10to12=True) | Q(thu12to3=True)
                                          | Q(thu3to6=True) | Q(thu6to9=True)),
                           DAY_FRIDAY: (Q(fri8to10=True) | Q(fri10to12=True) | Q(fri12to3=True)
                                        | Q(fri3to6=True) | Q(fri6to9=True)),
                           DAY_SATURDAY: (Q(sat8to10=True) | Q(sat10to12=True) | Q(sat12to3=True)
                                          | Q(sat3to6=True) | Q(sat6to9=True)),
                           DAY_SUNDAY: (Q(sun8to10=True) | Q(sun10to12=True) | Q(sun12to3=True)
                                        | Q(sun3to6=True) | Q(sun6to9=True))
                           }
                filter_bool = reduce(lambda x, y: x | y, [exp_dic.get(item) for item in query_serializer
                                     .validated_data.get('availability').split(',')]
                                     )
                qs = qs.filter(id__in=Availability.objects.filter(filter_bool).values_list('instructor_id'))
            if keys.get('place_for_lessons'):
                filter_bool = reduce(lambda x, y: x | y,
                                     [Q(**{item: True}) for item in query_serializer
                                        .validated_data.get('place_for_lessons').split(',')]
                                     )
                qs = qs.filter(id__in=InstructorPlaceForLessons.objects.filter(filter_bool).values_list('instructor_id'))
            if keys.get('student_ages'):
                filter_bool = reduce(lambda x, y: x | y,
                                     [Q(**{item: True}) for item in query_serializer
                                        .validated_data.get('student_ages').split(',')]
                                     )
                qs = qs.filter(id__in=InstructorAgeGroup.objects.filter(filter_bool).values_list('instructor_id'))
            if keys.get('qualifications'):
                filter_bool = reduce(lambda x, y: x | y,
                                     [Q(**{item: True}) for item in query_serializer
                                        .validated_data.get('qualifications').split(',')]
                                     )
                qs = qs.filter(id__in=InstructorAdditionalQualifications.objects.filter(filter_bool).values_list('instructor_id'))
            if keys.get('languages'):
                filter_bool = reduce(lambda x, y: x | y,
                                     [Q(languages__contains=[item, ]) for item in query_serializer
                                        .validated_data.get('languages').split(',')]
                                     )
                qs = qs.filter(filter_bool)
            if keys.get('gender'):
                qs = qs.filter(gender=query_serializer.validated_data.get('gender'))
            if keys.get('min_rate'):
                qs = qs.filter(instructorlessonrate__mins30__gte=query_serializer.validated_data.get('min_rate'))
            if keys.get('max_rate'):
                qs = qs.filter(instructorlessonrate__mins30__lte=query_serializer.validated_data.get('max_rate'))
            if keys.get('instruments'):
                instrument_list = query_serializer.validated_data.get('instruments', '').split(',')
                qs = qs.filter(id__in=InstructorInstruments.objects.filter(instrument__name__in=instrument_list)\
                               .values_list('instructor_id'))
            if isinstance(request.user, AnonymousUser):
                account = None
            else:
                account = get_account(request.user)
            if query_serializer.validated_data.get('location'):
                lat_value, lng_value = query_serializer.validated_data.get('location')
                coordinates = Point(lng_value, lat_value, srid=4326)
            elif account and account.coordinates:
                coordinates = account.coordinates
            else:
                coordinates = None
            if coordinates:
                qs = qs.filter(coordinates__isnull=False).filter(
                    coordinates__distance_lte=(coordinates, D(mi=query_serializer.validated_data.get('distance')))
                ).annotate(distance=Distance('coordinates', coordinates))
                if query_serializer.validated_data.get('sort'):
                    if query_serializer.validated_data['sort'] == 'rate':
                        qs = qs.order_by('instructorlessonrate__mins30', '-user__last_login')
                    elif query_serializer.validated_data['sort'] == '-rate':
                        qs = qs.order_by('-instructorlessonrate__mins30', '-user__last_login')
                    else:
                        qs = qs.order_by(query_serializer.validated_data['sort'], '-user__last_login')
                else:
                    qs = qs.order_by('-user__last_login')
            else:
                qs = qs.annotate(distance=Distance('coordinates', Cast(None, PointField())))
                if query_serializer.validated_data.get('sort'):
                    if query_serializer.validated_data['sort'] == 'rate':
                        qs = qs.order_by('instructorlessonrate__mins30', 'user__first_name')
                    elif query_serializer.validated_data['sort'] == '-rate':
                        qs = qs.order_by('-instructorlessonrate__mins30', 'user__first_name')
                    else:
                        qs = qs.order_by('-user__last_login')
                else:
                    qs = qs.order_by('-user__last_login')
            # return data with pagination
            paginator = PageNumberPagination()
            result_page = paginator.paginate_queryset(qs, request)
            serializer = sers.InstructorDataSerializer(result_page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        else:
            result = build_error_dict(query_serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class MinimalLessonRateView(views.APIView):
    permission_classes = (AllowAny, )

    def get(self, request):
        res = InstructorLessonRate.objects.aggregate(min_rate=Min('mins30'))
        return Response({'minRate': res['min_rate']})


class AffiliateRegisterView(views.APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        serializer = sers.AffiliateRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            ser = sers.AffiliateRegisterSerializer(user)
            return Response(ser.data)
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(views.APIView):
    """Return data for display in user dashboard"""

    def get(self, request):
        if request.user.is_instructor():
            serializer = InstructorDashboardSerializer(request.user.instructor)
            data = serializer.data.copy()
            next_lesson = Lesson.get_next_lesson(request.user)
            ser = ScheduledLessonSerializer(next_lesson, context={'user': request.user})
            data.update({'nextLesson': ser.data})
        elif request.user.is_parent():
            ser = sers.TiedStudentParentDashboardSerializer(request.user.parent.tied_students, many=True)
            data = {'students': ser.data, 'missingFields': [{'reviews': request.user.parent.get_missing_reviews()}]}
        elif request.user.is_student():
            ser = sers.StudentDashboardSerializer(request.user.student)
            data = {'students': [ser.data], 'missingFields': [{'reviews': request.user.student.get_missing_reviews()}]}
        else:
            return Response({})
        return Response(data)


class ReferralInfoView(views.APIView):
    """Get some user data from referral_token"""
    permission_classes = (AllowAny, )

    def get(self, request, token):
        try:
            user = User.objects.get(referral_token=token)
        except ObjectDoesNotExist:
            return Response({'detail': 'There is no user for provided token'}, status=status.HTTP_400_BAD_REQUEST)
        data = {'displayName': '', 'avatar': ''}
        account = get_account(user)
        if account:
            if account.display_name:
                data['displayName'] = account.display_name
            if account.avatar:
                data['avatar'] = account.avatar.url
        return Response(data)


class ReferralDashboardView(views.APIView):

    def get(self, request):
        qs = UserBenefits.objects.filter(beneficiary=request.user, status=BENEFIT_READY, benefit_type=BENEFIT_AMOUNT)
        ser = sers.ReferralDashboardSerializer(qs, many=True)
        response_data = ser.data.copy()
        total = qs.aggregate(total=Sum('benefit_qty'))
        if total['total'] is None:
            total['total'] = 0
        return Response({'totalAmount': total['total'], 'providerList': response_data})


class InstructorReviews(views.APIView):
    permission_classes = (AllowAny, )

    def post(self, request, pk, email=None):
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'detail': 'There is not user with provided email'}, status=status.HTTP_400_BAD_REQUEST)
            request.data['user'] = user.id
        else:
            if isinstance(request.user, AnonymousUser):
                return Response({'detail': "Can't register a review without user"}, status=status.HTTP_400_BAD_REQUEST)
            request.data['user'] = request.user.id
        request.data['instructor'] = pk
        ser = sers.CreateInstructorReviewSerializer(data=request.data)
        if ser.is_valid():
            obj = ser.save()
            task_log = TaskLog.objects.create(task_name='send_instructor_info_review', args={'obj_id': obj.id})
            info_instructor_review.delay(obj.id, task_log.id)
            ser_data = sers.ReturnCreateInstructorReviewSerializer(obj)
            return Response(ser_data.data)
        else:
            result = build_error_dict(ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk):
        try:
            instructor = Instructor.objects.get(id=pk)
        except Instructor.DoesNotExist:
            return Response({'detail': 'There is not instructor with provided id'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'instructorName': instructor.display_name})
