from datetime import timedelta
from logging import getLogger
from twilio.rest import Client

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import EmailMultiAlternatives
from django.db import transaction, IntegrityError
from django.db.models import ObjectDoesNotExist, Prefetch
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.template import loader
from django.utils import timezone

from rest_framework import status, views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import *
from rest_framework.response import Response

from core.constants import PHONE_TYPE_MAIN, ROLE_INSTRUCTOR, ROLE_STUDENT, HOSTNAME_PROTOCOL
from core.models import UserToken
from core.utils import generate_hash, get_date_a_month_later

from .models import Education, Employment, Instructor, Instrument, PhoneNumber, StudentDetails, TiedStudent, \
    get_account, get_user_phone

from .serializers import (
    AvatarInstructorSerializer, AvatarParentSerializer, AvatarStudentSerializer, GuestEmailSerializer,
    InstructorBuildJobPreferencesSerializer, InstructorCreateAccountSerializer, InstructorDataSerializer,
    InstructorDetailSerializer, InstructorEducationSerializer, InstructorEmploymentSerializer,
    InstructorProfileSerializer, ParentCreateAccountSerializer, StudentCreateAccountSerializer,
    StudentDetailsSerializer, TiedStudentSerializer, TiedStudentItemSerializer,
    UserEmailSerializer, UserInfoUpdateSerializer, UserPasswordSerializer,
)
from .utils import send_welcome_email, send_referral_invitation_email

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()
logger = getLogger('api_errors')

from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_user_response(account):
    user = account.user
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
        'lat': account.lat,
        'lng': account.lng,
        'referralToken': user.referral_token,
    }
    return data


def get_instructor_profile(user_cc):
    if user_cc.user.get_role() == ROLE_INSTRUCTOR:
        data = {
            'bioTitle': user_cc.bio_title,
            'bioDescription': user_cc.bio_description,
            'music': user_cc.music,
        }
        return data


class CreateAccount(views.APIView):
    permission_classes = ()

    @transaction.atomic()
    def post(self, request):
        account_serializer = self.get_serializer_class(request)
        serializer = account_serializer(data=request.data)
        if serializer is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if serializer.is_valid():
            user_cc = serializer.save()
            user_response = get_user_response(user_cc)
            user_response['token'] = get_tokens_for_user(user_cc.user)
            return Response(user_response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self, request):
        if request.data['role'] == 'parent':
            return ParentCreateAccountSerializer
        elif request.data['role'] == 'instructor':
            return InstructorCreateAccountSerializer
        elif request.data['role'] == 'student':
            return StudentCreateAccountSerializer


class LoginView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        form = AuthenticationForm(data={
            'username': request.data['email'],
            'password': request.data['password'],
        })
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            login(request, user)
            return Response(get_user_response(get_account(user)))
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(views.APIView):
    """For set a new password, when user forgot it."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = UserEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.data['email']
            user = User.objects.get(email=email)
            subject = "Reset Your Password"
            repeated_token = True
            while repeated_token:
                token = generate_hash(email)
                expired_time = timezone.now() + timedelta(days=1)
                try:
                    UserToken.objects.create(user=user, token=token, expired_at=expired_time)
                except IntegrityError:
                    pass
                else:
                    repeated_token = False
            target_url = '{}/forgot-password?token={}'.format(HOSTNAME_PROTOCOL, token)
            context = {'url_reset_pass': target_url}
            text_content = loader.render_to_string('reset_password_plain.html', context)
            html_content = loader.render_to_string('reset_password.html', context)
            from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
            email_message = EmailMultiAlternatives(subject, text_content, from_email, [email, ])
            email_message.attach_alternative(html_content, 'text/html')
            try:
                email_message.send()
            except Exception as e:
                logger.error(e)
        return Response({'message': 'Check your email to set a new password.'}, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = request.query_params.get('token')
            if token:
                try:
                    user_token = UserToken.objects.get(token=token)
                except ObjectDoesNotExist:
                    return Response({'message': 'Wrong token value'}, status=status.HTTP_400_BAD_REQUEST)
                if user_token.expired_at < timezone.now():
                    return Response({'message': 'Wrong token value'}, status=status.HTTP_400_BAD_REQUEST)
                passw = serializer.data['password']
                user_token.user.set_password(passw)
                user_token.user.save()
                user_token.delete()
                return Response({'message': 'Password set successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Token value is missing'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(views.APIView):
    def get(self, request):
        logout(request)
        return Response({'message': "You have successfully logged out."}, status=status.HTTP_200_OK)


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
        data = {
            'id': request.user.id,
            'email': request.user.email,
            'role': request.user.get_role(),
            'firstName': request.user.first_name,
            'middleName': account.middle_name,
            'lastName': request.user.last_name,
            'birthday': account.birthday,
            'phone': get_user_phone(account),
            'gender': account.gender,
            'location': account.location,
            'lat': account.lat,
            'lng': account.lng,
            'referralToken': request.user.referral_token,
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
            data['bioTitle'] = account.bio_title
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
            data['availability'] = {'mon8to10': instructor.availability.all()[0].mon8to10,
                                    'mon10to12': instructor.availability.all()[0].mon10to12,
                                    'mon12to3': instructor.availability.all()[0].mon12to3,
                                    'mon3to6': instructor.availability.all()[0].mon3to6,
                                    'mon6to9': instructor.availability.all()[0].mon6to9,
                                    'tue8to10': instructor.availability.all()[0].tue8to10,
                                    'tue10to12': instructor.availability.all()[0].tue10to12,
                                    'tue12to3': instructor.availability.all()[0].tue12to3,
                                    'tue3to6': instructor.availability.all()[0].tue3to6,
                                    'tue6to9': instructor.availability.all()[0].tue6to9,
                                    'wed8to10': instructor.availability.all()[0].wed8to10,
                                    'wed10to12': instructor.availability.all()[0].wed10to12,
                                    'wed12to3': instructor.availability.all()[0].wed12to3,
                                    'wed3to6': instructor.availability.all()[0].wed3to6,
                                    'wed6to9': instructor.availability.all()[0].wed6to9,
                                    'thu8to10': instructor.availability.all()[0].thu8to10,
                                    'thu10to12': instructor.availability.all()[0].thu10to12,
                                    'thu12to3': instructor.availability.all()[0].thu12to3,
                                    'thu3to6': instructor.availability.all()[0].thu3to6,
                                    'thu6to9': instructor.availability.all()[0].thu6to9,
                                    'fri8to10': instructor.availability.all()[0].fri8to10,
                                    'fri10to12': instructor.availability.all()[0].fri10to12,
                                    'fri12to3': instructor.availability.all()[0].fri12to3,
                                    'fri3to6': instructor.availability.all()[0].fri3to6,
                                    'fri6to9': instructor.availability.all()[0].fri6to9,
                                    'sat8to10': instructor.availability.all()[0].sat8to10,
                                    'sat10to12': instructor.availability.all()[0].sat10to12,
                                    'sat12to3': instructor.availability.all()[0].sat12to3,
                                    'sat3to6': instructor.availability.all()[0].sat3to6,
                                    'sat6to9': instructor.availability.all()[0].sat6to9,
                                    'sun8to10': instructor.availability.all()[0].sun8to10,
                                    'sun10to12': instructor.availability.all()[0].sun10to12,
                                    'sun12to3': instructor.availability.all()[0].sun12to3,
                                    'sun3to6': instructor.availability.all()[0].sun3to6,
                                    'sun6to9': instructor.availability.all()[0].sun6to9} \
                if instructor.availability.count() else {}
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
            data['employment'] = [{'employer': item.employer, 'jobTitle': item.job_title}
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
        data = {
            'id': None,
            'email': None,
        }
        if request.user.is_authenticated:
            data = get_instructor_profile(get_account(request.user))

        return Response(data)


class UpdateProfileView(views.APIView):
    def put(self, request):
        serializer = InstructorProfileSerializer(data=request.data, instance=Instructor.objects.get(user=request.user))
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'errors': serializer.errors})


class UpdateUserInfoView(views.APIView):
    def put(self, request):
        serializer = UserInfoUpdateSerializer(instance=request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneView(views.APIView):
    def post(self, request):
        try:
            phone = PhoneNumber.objects.get(user=request.user, number=request.data['phoneNumber'])
        except ObjectDoesNotExist:
            if PhoneNumber.objects.filter(user=request.user).exists():
                phone = PhoneNumber.objects.filter(user=request.user).update(number=request.data['phoneNumber'])
            else:
                phone = PhoneNumber.objects.create(user=request.user, number=request.data['phoneNumber'],
                                                   type=PHONE_TYPE_MAIN)
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification = client.verify \
            .services(settings.TWILIO_SERVICE_SID) \
            .verifications \
            .create(to=phone.number, channel=request.data['channel'])
        return Response({"sid": verification.sid, "status": verification.status,
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
        return Response({'status': verification_check.status, 'message': 'Phone validation was successful.'},
                        status=status.HTTP_200_OK if approved else status.HTTP_400_BAD_REQUEST)


class InstructorBuildJobPreferences(views.APIView):
    def post(self, request):
        serializer = InstructorBuildJobPreferencesSerializer(data=request.data,
                                                             instance=Instructor.objects.get(user=request.user))
        if serializer.is_valid():
            serializer.save()
            return Response(request.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstructorEducationView(views.APIView):
    def post(self, request):
        data = request.data.copy()
        data['instructor'] = request.user.instructor.pk
        serializer = InstructorEducationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        if hasattr(request.user.instructor, 'education'):
            serializer = InstructorEducationSerializer(request.user.instructor.education, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response([], status=status.HTTP_200_OK)


class InstructorEducationItemView(views.APIView):
    def put(self, request, pk):
        data = request.data.copy()
        data['instructor'] = request.user.instructor.pk
        try:
            educ_instance = Education.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"error": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = InstructorEducationSerializer(instance=educ_instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            educ_instance = Education.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"error": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        educ_instance.delete()
        return Response({"message": "success"}, status=status.HTTP_200_OK)


class InstructorDetailView(views.APIView):

    def get(self, request, pk):
        instructor = get_object_or_404(Instructor, pk=pk)
        serializer = InstructorDetailSerializer(instructor)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UploadAvatarView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request):
        serializer_class = self.get_serializer_class(request)
        account = get_account(request.user)
        serializer = serializer_class(instance=account, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": 'success'}, status=status.HTTP_200_OK)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self, request):
        role = request.user.get_role()
        if role == 'instructor':
            return AvatarInstructorSerializer
        elif role == 'parent':
            return AvatarParentSerializer
        else:
            return AvatarStudentSerializer


class ReferralInvitation(views.APIView):
    def post(self, request):
        serializer = GuestEmailSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            print(request.data['email'])
            email = request.data['email']
            try:
                send_referral_invitation_email(user, email)
            except Exception as e:
                return Response({
                    "error": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": 'Invitation sent successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class StudentDetailView(views.APIView):
    def put(self, request):
        data = request.data.copy()
        data['user'] = request.user.pk
        if request.user.student_details.count():
            serializer = StudentDetailsSerializer(instance=request.user.student_details, data=data, partial=True)
        else:
            serializer = StudentDetailsSerializer(data=data)
        if serializer.is_valid():
            if request.user.student_details.count():
                serializer.save()
            else:
                serializer.create(serializer.validated_data)
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        if request.user.student_details.count():
            serializer = StudentDetailsSerializer(request.user.student_details.first())
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({}, status=status.HTTP_200_OK)


class TiedStudentView(views.APIView):
    def post(self, request):
        # add parent's id to data student
        data = request.data.copy()
        data.update({'user': request.user.pk})
        serializer = TiedStudentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        serializer = TiedStudentSerializer(StudentDetails.objects.filter(user__id=request.user.pk), many=True)
        return Response(serializer.data)


class TiedStudentItemView(views.APIView):
    def put(self, request, pk):
        try:
            instance = StudentDetails.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"error": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TiedStudentItemSerializer(instance=instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            instance = StudentDetails.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"error": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        instance.tied_student.delete()
        instance.delete()
        return Response({"message": "success"}, status=status.HTTP_200_OK)


class InstructorEmploymentView(views.APIView):
    def post(self, request):
        serializer = InstructorEmploymentSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        if hasattr(request.user.instructor, 'employment'):
            serializer = InstructorEmploymentSerializer(request.user.instructor.employment, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response([], status=status.HTTP_200_OK)


class InstructorEmploymentItemView(views.APIView):
    def put(self, request, pk):
        try:
            instance = Employment.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"error": "Does not exist an object with provided id"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = InstructorEmploymentSerializer(instance=instance, data=request.data,
                                                    context={'user': request.user}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            instance = Employment.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({"error": "Does not exist an object with provided id"},
                            status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response({"message": "success"}, status=status.HTTP_200_OK)


class InstructorListView(views.APIView):

    def get(self, request):
        serializer = InstructorDataSerializer(Instructor.objects.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
