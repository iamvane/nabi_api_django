import stripe

from django.conf import settings
from django.db.models import Q

from rest_framework import status, views
from rest_framework.response import Response

from accounts.models import Instructor
from payments.models import Payment

from .client_provider import AccurateApiClient
from .models import BackgroundCheckRequest, BackgroundCheckStep
from .serializers import BGCheckRequestSerializer, InstructorIdSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


class BackgroundCheckRequestView(views.APIView):

    def post(self, request):
        """Create a request for instructor's check background"""
        # first, get instructor instance
        serializer = BGCheckRequestSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data.get('instructor_id'):
                instructor = Instructor.objects.get(id=serializer.validated_data['instructor_id'])
            else:
                instructor = request.user.instructor
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        resource_id = None

        # check if pending background check exists
        bg_request = BackgroundCheckRequest.objects.filter(user=instructor.user).last()
        if bg_request and bg_request.status == BackgroundCheckRequest.REQUESTED:
            return Response({'message': 'Background check in progress already'}, status=status.HTTP_400_BAD_REQUEST)
        # if does not exist, make the card charge, via stripe
        try:
            charge = stripe.Charge.create(amount='{:.0f}'.format(serializer.validated_data['amount'] * 100),
                                          currency='usd',
                                          source=serializer.validated_data['stripe_token'],
                                          description='Background Check Request')
        except stripe.error.CardError as ce:
            return Response(ce, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # register the charge done
        Payment.objects.create(user=request.user, amount=serializer.validated_data['amount'],
                               description='Background Check Request', charge_id=charge.id)
        # proceed with requests to Accurate
        if bg_request:
            # Get last step from bg_request. Would be create or update candidate
            if bg_request.status == BackgroundCheckRequest.PRELIMINARY:
                bg_step = BackgroundCheckStep.objects.filter(request=bg_request).last()
            else:
                bg_step = BackgroundCheckStep.objects.filter(Q(step='candidate_register') | Q(step='candidate_update'),
                                                             request=bg_request).last()
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
                        return Response(resp_dict, status=error)
                    bg_step = BackgroundCheckStep.objects.get(id=resp_dict['bg_step_id'])
                else:
                    resource_id = bg_step.resource_id
                    bg_step = None
        else:
            provider_client = AccurateApiClient('candidate')
            resp_dict = provider_client.create_candidate(instructor.user.instructor)
            error = resp_dict.pop('error_code')
            if error:
                return Response(resp_dict, status=error)
            bg_step = BackgroundCheckStep.objects.get(id=resp_dict['bg_step_id'])

        provider_client = AccurateApiClient('order')
        if resource_id is None:
            resp_dict = provider_client.place_order(instructor.user, bg_step.resource_id, bg_step)
        else:
            resp_dict = provider_client.place_order(instructor.user, resource_id, bg_step)
        error = resp_dict.pop('error_code')
        if error:
            return Response(resp_dict, status=error)
        else:   # error == 0, no error
            return Response({'message': 'success'}, status=status.HTTP_200_OK)


class BackgroundCheckView(views.APIView):
    """If bg request is not register as complete or cancelled, make a request to Accurate, to get status."""

    def get(self, request):
        """Get last background check request"""
        if request.query_params.get('instructorId'):
            serializer = InstructorIdSerializer(data=request.query_params)
            if serializer.is_valid():
                instructor = Instructor.objects.get(id=serializer.data['instructor_id'])
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            instructor = request.user.instructor
        bg_request = BackgroundCheckRequest.objects.filter(user=instructor.user).last()
        if bg_request:
            if bg_request.status == BackgroundCheckRequest.CANCELLED:
                return Response({'status': 'CANCELLED'}, status=status.HTTP_200_OK)
            elif bg_request.status == BackgroundCheckRequest.COMPLETE:
                return Response({'status': 'COMPLETE'}, status=status.HTTP_200_OK)
            else:
                provider_client = AccurateApiClient('order')
                resp_dict = provider_client.check_order(instructor.user)
                error = resp_dict.pop('error_code')
                if error:
                    return Response(resp_dict, status=error)
                else:  # error == 0, no error
                    return Response({'status': resp_dict['msg']['status']}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'No background check request for this user'}, status=status.HTTP_404_NOT_FOUND)
