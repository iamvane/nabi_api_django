from django.db.models import ObjectDoesNotExist

from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.constants import ROLE_PARENT, ROLE_STUDENT
from core.permissions import AccessForInstructor

from .models import LessonRequest
from . import serializers as sers


class LessonRequestView(views.APIView):

    def post(self, request):
        """Register a lesson request. Works for student and parent users"""
        data = request.data.copy()
        data['user_id'] = request.user.id
        role = request.user.get_role()
        if role == ROLE_STUDENT:
            ser = sers.LessonRequestSerializer(data=data, context={'is_parent': False})
        elif role == ROLE_PARENT:
            ser = sers.LessonRequestSerializer(data=data, context={'is_parent': True})
        else:
            return Response({'message': "You are not enabled to request for lessons"},
                            status=status.HTTP_400_BAD_REQUEST)
        if ser.is_valid():
            obj = ser.save()
            return Response({'object_id': obj.id}, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """Get a list of lesson requests, registered by current user"""
        ser = sers.LessonRequestDetailSerializer(request.user.lesson_requests.all(), many=True)
        return Response(ser.data, status=status.HTTP_200_OK)


class LessonRequestItemView(views.APIView):

    def put(self, request, pk):
        """Update an existing lesson request"""
        try:
            instance = LessonRequest.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data['user_id'] = request.user.id
        role = request.user.get_role()
        if role == ROLE_STUDENT:
            ser = sers.LessonRequestSerializer(data=data, instance=instance, context={'is_parent': False}, partial=True)
        elif role == ROLE_PARENT:
            ser = sers.LessonRequestSerializer(data=data, instance=instance, context={'is_parent': True}, partial=True)
        else:
            return Response({'message': "You are not enabled to request for lessons"},
                            status=status.HTTP_400_BAD_REQUEST)
        if ser.is_valid():
            ser.save()
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete an existing lesson request"""
        try:
            lesson_request = LessonRequest.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        lesson_request.delete()
        return Response({'message': 'success'}, status=status.HTTP_200_OK)

    def get(self, request, pk):
        """Get data from existing lesson request"""
        try:
            lesson_request = LessonRequest.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonRequestDetailSerializer(lesson_request)
        return Response(ser.data, status=status.HTTP_200_OK)


class ApplicationView(views.APIView):
    permission_classes = (IsAuthenticated, AccessForInstructor)

    def post(self, request):
        data = request.data.copy()
        data['instructor_id'] = request.user.instructor.id
        ser = sers.ApplicationCreateSerializer(data=data)
        if ser.is_valid():
            ser.save()
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
