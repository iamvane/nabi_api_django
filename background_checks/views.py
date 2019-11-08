from django.db.models import Q

from rest_framework import status, views

from rest_framework.response import Response

from .client_provider import AccurateApiClient
from .models import BackgroundCheckRequest, BackgroundCheckStep


class BackgroundCheckRequestView(views.APIView):

    def get(self, request):
        resource_id = None
        bg_request = BackgroundCheckRequest.objects.filter(user=request.user).last()
        if bg_request:
            # Get last step from bg_request. Would be create or update candidate
            if bg_request.status == BackgroundCheckRequest.PRELIMINARY:
                bg_step = BackgroundCheckStep.objects.filter(request=bg_request).last()
            elif bg_request.status == BackgroundCheckRequest.REQUESTED:
                return Response({'msg': 'Background check in progress already'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                bg_step = BackgroundCheckStep.objects.filter(Q(step='candidate_register') | Q(step='candidate_update'),
                                                             request=bg_request).last()
                if bg_step.data['firstName'] != request.user.first_name \
                        or bg_step.data['lastName'] != request.user.last_name \
                        or bg_step.data['email'] != request.user.email:
                    provider_client = AccurateApiClient('candidate')
                    resp_dict = provider_client.update_candidate(request.user.instructor,
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
            resp_dict = provider_client.create_candidate(request.user.instructor)
            error = resp_dict.pop('error_code')
            if error:
                return Response(resp_dict, status=error)
            bg_step = BackgroundCheckStep.objects.get(id=resp_dict['bg_step_id'])

        provider_client = AccurateApiClient('order')
        if resource_id is None:
            resp_dict = provider_client.place_order(request.user, bg_step.resource_id, bg_step)
        else:
            resp_dict = provider_client.place_order(request.user, resource_id, bg_step)
        error = resp_dict.pop('error_code')
        if error:
            return Response(resp_dict, status=error)
        else:   # error == 0, no error
            return Response({'msg': 'success'}, status=status.HTTP_200_OK)


class BackgroundCheckView(views.APIView):

    def get(self, request):
        """Get last background check request"""
        bg_request = BackgroundCheckRequest.objects.filter(user=request.user).last()
        if bg_request:
            if bg_request.status == BackgroundCheckRequest.CANCELLED:
                return Response({'error': 'Last background check was cancelled'}, status=status.HTTP_404_NOT_FOUND)
            elif bg_request.status == BackgroundCheckRequest.COMPLETE:
                return Response({'msg': 'complete'}, status=status.HTTP_200_OK)
            else:
                provider_client = AccurateApiClient('order')
                resp_dict = provider_client.check_order(request.user)
                error = resp_dict.pop('error_code')
                if error:
                    return Response(resp_dict, status=error)
                else:  # error == 0, no error
                    return Response({'msg': 'Order is {}'.format(resp_dict['msg']['status'])},
                                    status=status.HTTP_200_OK)
        else:
            return Response({'error': 'No background check request for this user'}, status=status.HTTP_404_NOT_FOUND)
