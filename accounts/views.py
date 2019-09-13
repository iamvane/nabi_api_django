from datetime import timedelta
from logging import getLogger
from twilio.rest import Client

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import EmailMultiAlternatives
from django.db import transaction, IntegrityError
from django.db.models import ObjectDoesNotExist
from django.middleware.csrf import get_token
from django.template import loader
from django.utils import timezone

from rest_framework import views, status
from rest_framework.permissions import *
from rest_framework.response import Response

from core.models import UserToken
from core.utils import generate_hash

from .models import Instructor, Parent, PhoneNumber, Student, get_user_phones
from .serializers import (
    InstructorAccountInfoSerializer, InstructorAccountStepTwoSerializer, InstructorCreateAccountSerializer,
    InstructorProfileSerializer, ParentCreateAccountSerializer, StudentCreateAccountSerializer, UserEmailSerializer,
    UserPasswordSerializer, ROLE_INSTRUCTOR, ROLE_PARENT
)

User = get_user_model()
logger = getLogger('api_errors')


def get_user_response(user_cc):
    user = user_cc.user
    return {
        'id': user.id,
        'email': user.email,
        'role': user.get_role(),
        'first_name': user.first_name,
        'middle_name': user_cc.middle_name,
        'last_name': user.last_name,
        'birthday': user_cc.birthday,
        'phones': get_user_phones(user_cc),
        'gender': user_cc.gender,
        'location': user_cc.location,
        'lat': user_cc.lat,
        'lng': user_cc.lng,
    }


def get_user(user):
    if user.get_role() == ROLE_INSTRUCTOR:
        return Instructor.objects.filter(user=user).first()
    if user.get_role() == ROLE_PARENT:
        return Parent.objects.filter(user=user).first()
    return Student.objects.filter(user=user).first()


class CreateAccount(views.APIView):
    permission_classes = (AllowAny,)

    @transaction.atomic()
    def post(self, request):
        account_serializer = self.get_serializer_class(request)
        serializer = account_serializer(data=request.data)
        if serializer is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if serializer.is_valid():
            user_cc = serializer.save()
            login(request, user_cc.user)
            return Response(get_user_response(user_cc))
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
            return Response(get_user_response(get_user(user)))
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(views.APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        serializer = UserEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.data['email']
            user = User.objects.get(email=email)
            subject = "Reset Password"
            email_template_name = 'accounts/email_reset_password.html'
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
            target_url = '{}/forgot-password?token={}'.format(settings.HOSTNAME_PROTOCOL, token)
            context = {'full_name': user.get_full_name(), 'url_reset_pass': target_url}
            body = loader.render_to_string(email_template_name, context)
            email_message = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [email, ])
            html_email = loader.render_to_string(email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')
            try:
                email_message.send()
            except Exception as e:
                logger.error(e)
        return Response({'message': 'success'}, status=status.HTTP_200_OK)


class SetPasswordView(views.APIView):
    """To set a password, when user forgot it."""
    permission_classes = (AllowAny, )

    def post(self, request):
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
                return Response({'message': 'Password set successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Token value is missing'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CsrfTokenView(views.APIView):

    def get(self, request):
        return Response({'token': get_token(request)})


class WhoAmIView(views.APIView):

    def get(self, request):
        data = {
            'id': None,
            'email': None,
        }
        if request.user.is_authenticated:
            data = get_user_response(get_user(request.user))

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
        serializer = InstructorAccountInfoSerializer(data=request.data,
                                                     instance=Instructor.objects.get(user=request.user))
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneView(views.APIView):

    def post(self, request):
        phone = PhoneNumber.objects.get(user=request.user, phone_number=request.data['phone_number'])
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification = client.verify \
            .services(settings.TWILIO_SERVICE_SID) \
            .verifications \
            .create(to=phone.phone_number, channel=request.data['channel'])
        return Response({"sid": verification.sid, "status": verification.status})

    def put(self, request):
        phone = PhoneNumber.objects.get(user=request.user, phone_number=request.data['phone_number'])
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification_check = client.verify \
            .services(settings.TWILIO_SERVICE_SID) \
            .verification_checks \
            .create(to=phone.phone_number, code=request.data['code'])
        approved = verification_check.status == 'approved'
        if approved:
            phone.phone_verified_at = timezone.now()
            phone.save()
        return Response({'status': verification_check.status},
                        status=status.HTTP_200_OK if approved else status.HTTP_400_BAD_REQUEST)


class InstructorStep2View(views.APIView):

    def post(self, request):
        serializer = InstructorAccountStepTwoSerializer(data=request.data,
                                                        instance=Instructor.objects.get(user=request.user))
        if serializer.is_valid():
            serializer.save()
            return Response(request.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
