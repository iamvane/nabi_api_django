from django.db.models import ObjectDoesNotExist

from rest_framework import status, views
from rest_framework.response import Response

from core.constants import ROLE_PARENT, ROLE_STUDENT

from .models import LessonRequest
from .serializers import LessonRequestSerializer


class LessonRequestView(views.APIView):

    def post(self, request):
        data = request.data.copy()
        data['user_id'] = request.user.id
        role = request.user.get_role()
        if role == ROLE_STUDENT:
            ser = LessonRequestSerializer(data=data, context={'is_parent': False})
        elif role == ROLE_PARENT:
            ser = LessonRequestSerializer(data=data, context={'is_parent': True})
        else:
            return Response({'message': "You are not enabled to request for lessons"},
                            status=status.HTTP_400_BAD_REQUEST)
        if ser.is_valid():
            ser.save()
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonRequestItemView(views.APIView):

    def put(self, request, pk):
        try:
            instance = LessonRequest.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data['user_id'] = request.user.id
        role = request.user.get_role()
        if role == ROLE_STUDENT:
            ser = LessonRequestSerializer(data=data, instance=instance, context={'is_parent': False}, partial=True)
        elif role == ROLE_PARENT:
            ser = LessonRequestSerializer(data=data, instance=instance, context={'is_parent': True}, partial=True)
        else:
            return Response({'message': "You are not enabled to request for lessons"},
                            status=status.HTTP_400_BAD_REQUEST)
        if ser.is_valid():
            ser.save()
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            lesson_request = LessonRequest.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        lesson_request.delete()
        return Response({'message': 'success'}, status=status.HTTP_200_OK)
