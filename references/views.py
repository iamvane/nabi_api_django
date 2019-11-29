from django.conf import settings

from rest_framework import status, views
from rest_framework.response import Response

from core.utils import send_email

from .serializers import RegisterRequestReferenceSerializer


class RegisterRequestReferenceView(views.APIView):

    def post(self, request):
        serializer = RegisterRequestReferenceSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            for email in serializer.validated_data['emails']:
                from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
                send_email(from_email, email, 'Request for reference',
                           template='references/reference_email.html',
                           template_plain='references/reference_email_plain.html',
                           template_params={'full_name': request.user.get_full_name(),
                                            'first_name': request.user.first_name,
                                            'form_url': settings.GOOGLE_FORM_REFERENCES_URL}
                           )
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
