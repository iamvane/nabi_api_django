from rest_framework import status, views
from rest_framework.response import Response

from core.constants import ROLE_PARENT, ROLE_STUDENT

from .serializers import LessonRequestCreateSerializer


class LessonRequestView(views.APIView):

    def post(self, request):
        data = request.data.copy()
        data['user_id'] = request.user.id
        role = request.user.get_role()
        if role == ROLE_STUDENT:
            ser = LessonRequestCreateSerializer(data=data, context={'is_parent': False})
        elif role == ROLE_PARENT:
            ser = LessonRequestCreateSerializer(data=data, context={'is_parent': True})
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
        return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
