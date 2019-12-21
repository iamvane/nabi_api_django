import math

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Case, F, ObjectDoesNotExist, When

from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.constants import ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT
from core.permissions import AccessForInstructor

from . import serializers as sers
from .models import Application, LessonRequest


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
            ser = sers.LessonRequestDetailSerializer(obj)
            return Response(ser.data, status=status.HTTP_200_OK)
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
    """Create or retrieve applications for lesson request"""
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

    def get(self, request):
        ser = sers.ApplicationListSerializer(Application.objects.filter(instructor=request.user.instructor), many=True)
        return Response(ser.data, status=status.HTTP_200_OK)


class LessonRequestList(views.APIView):
    """API for get a list of lesson requests made for parents or students"""

    def get(self, request):
        role = request.user.get_role()
        if role != ROLE_INSTRUCTOR:
            return Response({'message': 'Access denied'}, status=status.HTTP_400_BAD_REQUEST)
        qs = LessonRequest.objects
        query_ser = sers.LessonRequestListQueryParamsSerializer(data=request.query_params.dict())
        if query_ser.is_valid():
            keys = dict.fromkeys(query_ser.validated_data, 1)
            point = None
            distance = None
            if (keys.get('lat') and not keys.get('lng')) or (keys.get('lng') and not keys.get('lat')):
                return Response({'message': "Both latitude and longitude values should be send"},
                                status=status.HTTP_400_BAD_REQUEST)
            elif keys.get('lat') and keys.get('lng'):
                point = Point(query_ser.validated_data['lat'], query_ser.validated_data['lng'])
            if keys.get('distance'):
                distance = query_ser.validated_data['distance']
            if point and distance is None:
                distance = 50
            if point is None and distance is not None:
                point = request.user.instructor.coordinates
            if point and distance is not None:
                qs = qs.annotate(coords=Case(
                    When(user__parent__isnull=False, then=F('user__parent__coordinates')),
                    When(user__student__isnull=False, then=F('user__student__coordinates')),
                    default=None)
                ).filter(coords__isnull=False).annotate(distance=Distance('coords', point)) \
                    .filter(distance__lte=distance)
            if keys.get('instrument'):
                qs = qs.filter(instrument__name=query_ser.validated_data.get('instrument'))
            if keys.get('place_for_lessons'):
                qs = qs.filter(place_for_lessons=query_ser.validated_data['place_for_lessons'])
            if keys.get('min_age') or keys.get('max_age'):
                qs = [item for item in qs.all() if
                      item.has_accepted_age(min_age=query_ser.validated_data.get('min_age'),
                                            max_age=query_ser.validated_data.get('max_age'))
                      ]
        else:
            return Response(query_ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonRequestItemSerializer(qs, many=True, context={'user_id': request.user.id})
        if point and distance is not None:
            returned_data = sorted(ser.data,
                                   key=lambda item: item.get('distance') if item.get('distance') is not None else math.inf)
        else:
            returned_data = ser.data
        return Response(returned_data, status=status.HTTP_200_OK)
