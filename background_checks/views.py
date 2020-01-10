import json
import stripe

from django.conf import settings
from django.db.models import ObjectDoesNotExist, Q
from django.utils import timezone

from rest_framework import status, views
from rest_framework.response import Response

from accounts.models import Instructor
from core.constants import *
from core.utils import send_admin_email
from payments.models import Payment

from . import serializers as sers
from .client_provider import AccurateApiClient, CANDIDATE_REGISTER_STEP, CANDIDATE_UPDATE_STEP, ORDER_PLACE_STEP
from .models import BackgroundCheckRequest, BackgroundCheckStep

stripe.api_key = settings.STRIPE_SECRET_KEY

MESSAGE = """The background check request with id {bg_id} wasn't registered in complete way; fail occurs in {step} step.

Background check was requested by user with email {email} (id: {user_id}), to instructor {ins_name} (id: {ins_id}), at {today}.

Obtained error code: {error_code}, error info: {error_info}.
"""


class BackgroundCheckRequestView(views.APIView):
    """Create or retrieve a background check request"""

    def post(self, request):
        """Create a request for instructor's check background"""
        # first, get instructor instance
        serializer = sers.BGCheckRequestSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data.get('instructor_id'):
                instructor = Instructor.objects.get(id=serializer.validated_data['instructor_id'])
            else:
                instructor = request.user.instructor
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        resource_id = None

        # check if pending background check exists
        last_bg_request = BackgroundCheckRequest.objects.filter(instructor=instructor).last()
        if last_bg_request and (last_bg_request.status == BackgroundCheckRequest.REQUESTED
                                or last_bg_request.status == BackgroundCheckRequest.PRELIMINARY):
            return Response({'message': 'Background check in progress already'}, status=status.HTTP_400_BAD_REQUEST)

        # Make card charge, via stripe
        try:
            charge = stripe.Charge.create(
                amount='{:.0f}'.format(serializer.validated_data['amount'] * 100),
                currency='usd',
                source=serializer.validated_data['stripe_token'],
                description='BackgroundCheck request for instructor {dname} ({inst_id}), requestor: {email}'.format(
                    dname=instructor.display_name, inst_id=instructor.id, email=request.user.email)
            )
        except stripe.error.CardError as ce:
            return Response(ce, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # register the charge done and service request
        payment = Payment.objects.create(
            user=request.user,
            amount=serializer.validated_data['amount'],
            description='BackgroundCheck request for instructor {dname} ({inst_id}), requestor: {email}'.format(
                dname=instructor.display_name, inst_id=instructor.id, email=request.user.email),
            charge_id=charge.id
        )
        current_bg_request = BackgroundCheckRequest.objects.create(user=request.user, instructor=instructor,
                                                                   observation='Payment done', payment=payment)

        # Proceed with requests to Accurate. From here, response is 200 code always
        if last_bg_request:
            # Get last step from last_bg_request, to check if candidate update is required
            bg_step = BackgroundCheckStep.objects.filter(Q(step=CANDIDATE_REGISTER_STEP) | Q(step=CANDIDATE_UPDATE_STEP),
                                                         request_id__in=BackgroundCheckRequest.objects.filter(
                                                             instructor=instructor).values_list('id', flat=True)
                                                         ).last()
            if bg_step.data['firstName'] != instructor.user.first_name \
                    or bg_step.data['lastName'] != instructor.user.last_name \
                    or bg_step.data['email'] != instructor.user.email:
                provider_client = AccurateApiClient('candidate')
                resp_dict = provider_client.update_candidate(instructor.user.instructor,
                                                             {'firstName': bg_step.data['firstName'],
                                                              'lastName': bg_step.data['lastName'],
                                                              'email': bg_step.data['email']}
                                                             )
                error = resp_dict.pop('error_code')
                if error:
                    send_admin_email('[ALERT] Background check request incomplete',
                                     MESSAGE.format(bg_id=current_bg_request.id, step=CANDIDATE_UPDATE_STEP,
                                                    user_id=request.user.id, email=request.user.email,
                                                    ins_id=instructor.id, ins_name=instructor.display_name,
                                                    today=timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                    error_code=error, error_info=json.dumps(resp_dict)
                                                    )
                                     )
                    return Response({'message': 'registered'}, status=status.HTTP_200_OK)
                bg_step = BackgroundCheckStep.objects.get(id=resp_dict['bg_step_id'])
            else:
                resource_id = bg_step.resource_id
                bg_step = None
        else:
            provider_client = AccurateApiClient('candidate')
            resp_dict = provider_client.create_candidate(current_bg_request.id, instructor.user.instructor)
            error = resp_dict.pop('error_code')
            if error:
                send_admin_email('[ALERT] Background check request incomplete',
                                 MESSAGE.format(bg_id=current_bg_request.id, step=CANDIDATE_REGISTER_STEP,
                                                user_id=request.user.id, email=request.user.email,
                                                ins_id=instructor.id, ins_name=instructor.display_name,
                                                today=timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                error_code=error, error_info=json.dumps(resp_dict)
                                                ),
                                 )
                return Response({'message': 'registered'}, status=status.HTTP_200_OK)
            bg_step = BackgroundCheckStep.objects.get(id=resp_dict['bg_step_id'])

        provider_client = AccurateApiClient('order')
        if resource_id is None:
            resp_dict = provider_client.place_order(current_bg_request.id, instructor.user, bg_step.resource_id, bg_step)
        else:
            resp_dict = provider_client.place_order(current_bg_request.id, instructor.user, resource_id, bg_step)
        error = resp_dict.pop('error_code')
        if error:
            send_admin_email('[ALERT] Background check request incomplete',
                             MESSAGE.format(bg_id=current_bg_request.id, step=ORDER_PLACE_STEP,
                                            user_id=request.user.id, email=request.user.email,
                                            ins_id=instructor.id, ins_name=instructor.display_name,
                                            today=timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            error_code=error, error_info=json.dumps(resp_dict)
                                            ),
                             )
            return Response({'message': 'registered'}, status=status.HTTP_200_OK)
        else:   # error == 0, no error
            # update payment data
            payment.status = PY_PROCESSED
            payment.save()
            return Response({'message': 'success'}, status=status.HTTP_200_OK)

    def get(self, request):
        """Get stored data from last registered background check request for an instructor"""
        if request.query_params.get('instructorId'):
            serializer = sers.InstructorIdSerializer(data=request.query_params)
            if serializer.is_valid():
                instructor = Instructor.objects.get(id=serializer.data['instructor_id'])
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                instructor = request.user.instructor
            except ObjectDoesNotExist:
                return Response({'message': 'User should be instructor or provide an instructorId'},
                                status=status.HTTP_400_BAD_REQUEST)
        bg_request = BackgroundCheckRequest.objects.filter(instructor=instructor).last()
        serializer = sers.BGCheckRequestModelSerializer(bg_request)
        if bg_request:
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'No background check request for this instructor'},
                            status=status.HTTP_400_BAD_REQUEST)


class BackgroundCheckStatusView(views.APIView):
    """Make a request to Accurate, to get status, if background request is not register as complete or cancelled;
    return stored data otherwise."""

    def get(self, request):
        """Get last background check request"""
        if request.query_params.get('instructorId'):
            serializer = sers.InstructorIdSerializer(data=request.query_params)
            if serializer.is_valid():
                instructor = Instructor.objects.get(id=serializer.data['instructor_id'])
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            instructor = request.user.instructor
        bg_request = BackgroundCheckRequest.objects.filter(instructor=instructor).last()
        if bg_request:
            if bg_request.status == BackgroundCheckRequest.CANCELLED \
                    or bg_request.status == BackgroundCheckRequest.COMPLETE:
                return Response({'requestId': bg_request.id, 'status': bg_request.status.upper(),
                                 'result': bg_request.provider_results.get('result'),
                                 'observation': bg_request.observation,
                                 'createdAt': bg_request.created_at.strftime('%Y-%m-%d %H:%M:%S')},
                                status=status.HTTP_200_OK)
            else:
                provider_client = AccurateApiClient('order')
                resp_dict = provider_client.check_order(instructor.user)
                error = resp_dict.pop('error_code')
                if error:
                    return Response(resp_dict, status=error)
                else:  # error == 0, no error
                    bg_request.refresh_from_db()
                    return Response({'requestId': bg_request.id, 'status': resp_dict['msg']['status'],
                                     'result': resp_dict['msg']['result'],
                                     'observation': bg_request.observation,
                                     'percentageComplete': resp_dict['msg']['percentageComplete'],
                                     'createdAt': bg_request.created_at.strftime('%Y-%m-%d %H:%M:%S')},
                                    status=status.HTTP_200_OK)
        else:
            return Response({'error': 'No background check request for this instructor'},
                            status=status.HTTP_400_BAD_REQUEST)
