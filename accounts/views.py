from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.middleware.csrf import get_token
from django.conf import settings
from rest_framework import views, status
from rest_framework.permissions import *
from rest_framework.response import Response
from .serializers import *
from .models import Parent, Instructor, Student
from twilio.rest import Client


def get_user_response(user_cc):
    user = user_cc.user
    return {
        'id': user.id,
        'email': user.email,
        'role': user.get_type(),
    }


def get_user(user):
    if user.get_type() == ROLE_INSTRUCTOR:
        return Instructor.objects.filter(user=user).first()
    if user.get_type() == ROLE_PARENT:
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
