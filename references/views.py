from django.conf import settings

from rest_framework import status, views
from rest_framework.response import Response

from core.utils import build_error_dict, send_email

from .models import ReferenceRequest
from .serializers import RegisterRequestReferenceSerializer


class RegisterRequestReferenceView(views.APIView):

    def post(self, request):
        serializer = RegisterRequestReferenceSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            for email in serializer.validated_data['emails']:
                from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
                send_email(from_email, email, 'Reference for {}'.format(request.user.first_name),
                           template='references/reference_email.html',
                           template_plain='references/reference_email_plain.html',
                           template_params={'full_name': request.user.get_full_name(),
                                            'first_name': request.user.first_name,
                                            'form_url': settings.GOOGLE_FORM_REFERENCES_URL}
                           )
            qs = ReferenceRequest.objects.filter(user=request.user).order_by('email')
            if qs.count():
                list_emails = [item.email for item in qs]
            else:
                list_emails = []
            return Response({'emails': list_emails})
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class RequestReferencesListView(views.APIView):
    """Get a list of requested references for this user"""

    def get(self, request):
        qs = ReferenceRequest.objects.filter(user=request.user).order_by('email')
        if qs.count():
            list_emails = [item.email for item in qs]
        else:
            list_emails = []
        return Response({'emails': list_emails})
