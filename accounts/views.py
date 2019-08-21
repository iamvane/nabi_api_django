from django.db import transaction
from rest_framework import views, status
from rest_framework.permissions import *
from rest_framework.response import Response
from .serializers import *


def get_user_response(user_cc):
    user = user_cc.user
    return {
        'id': user.id,
        'email': user.email,
    }


class CreateAccount(views.APIView):
    permission_classes = (AllowAny,)

    @transaction.atomic()
    def post(self, request):
        account_serializer = self.get_serializer_class(request)
        serializer = account_serializer(data=request.data)
        if serializer is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if serializer.is_valid():
            user = serializer.save()
            return Response(get_user_response(user))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self, request):
        if request.data['type'] == 'parent':
            return ParentCreateAccountSerializer
