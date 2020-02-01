import stripe
from functools import reduce

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.db.models import PointField
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import transaction
from django.db.models import Case, F, ObjectDoesNotExist, Q, When
from django.db.models.functions import Cast

from rest_framework import status, views
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import get_account
from core.constants import *
from core.models import TaskLog
from core.permissions import AccessForInstructor, AccessForParentOrStudent
from payments.models import Payment

from . import serializers as sers
from .models import Application, GradedLesson, LessonBooking, LessonRequest
from .tasks import send_application_alert, send_booking_alert, send_booking_invoice, send_request_alert_instructors

stripe.api_key = settings.STRIPE_SECRET_KEY


class LessonRequestView(views.APIView):
    """View for usage of parents and students."""
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def post(self, request):
        """Register a lesson request."""
        data = request.data.copy()
        data['user_id'] = request.user.id
        if request.user.is_parent():
            ser = sers.LessonRequestSerializer(data=data, context={'is_parent': True})
        else:
            ser = sers.LessonRequestSerializer(data=data, context={'is_parent': False})
        if ser.is_valid():
            obj = ser.save()
            task_log = TaskLog.objects.create(task_name='send_request_alert_instructors',
                                              args={'request_id': obj.id})
            send_request_alert_instructors.delay(obj.id, task_log.id)
            ser = sers.LessonRequestDetailSerializer(obj)
            return Response(ser.data, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """Get a list of lesson requests, registered by current user"""
        ser = sers.LessonRequestDetailSerializer(request.user.lesson_requests.exclude(status=LESSON_REQUEST_CLOSED),
                                                 many=True)
        return Response(ser.data, status=status.HTTP_200_OK)


class LessonRequestItemView(views.APIView):
    """View for usage of parents and students."""
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def put(self, request, pk):
        """Update an existing lesson request"""
        try:
            instance = LessonRequest.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data['user_id'] = request.user.id
        if request.user.is_parent():
            ser = sers.LessonRequestSerializer(data=data, instance=instance, context={'is_parent': True}, partial=True)
        else:
            ser = sers.LessonRequestSerializer(data=data, instance=instance, context={'is_parent': False}, partial=True)
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


class LessonRequestListView(views.APIView):
    """API for get a list of lesson requests created by parents or students"""
    permission_classes = (AllowAny, )

    def get(self, request):
        if isinstance(request.user, AnonymousUser):
            account = None
        else:
            account = get_account(request.user)
        qs = LessonRequest.objects.exclude(status=LESSON_REQUEST_CLOSED).annotate(coords=Case(
            When(user__parent__isnull=False, then=F('user__parent__coordinates')),
            When(user__student__isnull=False, then=F('user__student__coordinates')),
            default=None,
            output_field=PointField())
        )
        query_ser = sers.LessonRequestListQueryParamsSerializer(data=request.query_params.dict())
        if query_ser.is_valid():
            keys = dict.fromkeys(query_ser.validated_data, 1)
            point = None
            distance = None
            if keys.get('location'):
                point = Point(query_ser.validated_data['location'][1], query_ser.validated_data['location'][0])
            if keys.get('distance'):
                distance = query_ser.validated_data['distance']
            if point and distance is None:
                distance = 50
            if point is None and distance is not None:
                if account:
                    point = account.coordinates
            if point and distance is not None:
                qs = qs.filter(coords__isnull=False).filter(coords__distance_lte=(point, D(mi=distance)))\
                    .annotate(distance=Distance('coords', point))
            else:
                if account and account.coordinates:
                    qs = qs.annotate(distance=Distance('coords', account.coordinates))
                else:
                    qs = qs.annotate(distance=Distance('coords', Cast(None, PointField())))
            if keys.get('instrument'):
                qs = qs.filter(instrument__name=query_ser.validated_data.get('instrument'))
            if keys.get('place_for_lessons'):
                bool_filters = reduce(lambda x, y: x | y,
                                      [Q(place_for_lessons=item) for item in query_ser.validated_data.get('place_for_lessons')]
                                      )
                qs = qs.filter(bool_filters)
            qs = qs.order_by('-id')
            if keys.get('age'):
                if query_ser.validated_data.get('age') == AGE_CHILD:
                    min_age, max_age = 0, 12
                elif query_ser.validated_data.get('age') == AGE_TEEN:
                    min_age, max_age = 13, 17
                elif query_ser.validated_data.get('age') == AGE_ADULT:
                    min_age, max_age = 18, 65
                else:
                    min_age, max_age = 65, 150
                qs = [item for item in qs.all() if item.has_accepted_age(min_age=min_age, max_age=max_age)]
        else:
            return Response(query_ser.errors, status=status.HTTP_400_BAD_REQUEST)

        # return data with pagination
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(qs, request)
        if account:
            ser = sers.LessonRequestItemSerializer(result_page, many=True, context={'user_id': request.user.id})
        else:
            ser = sers.LessonRequestItemSerializer(result_page, many=True)
        return paginator.get_paginated_response(ser.data)


class LessonRequestItemListView(views.APIView):
    """Return data of a lesson request created by a parent or student"""

    def get(self, request, pk):
        try:
            lesson_request = LessonRequest.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provider id'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = sers.LessonRequestListItemSerializer(lesson_request, context={'user': request.user})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApplicationView(views.APIView):
    """Create or retrieve applications for lesson request"""
    permission_classes = (IsAuthenticated, AccessForInstructor)

    def post(self, request):
        data = request.data.copy()
        data['instructor_id'] = request.user.instructor.id
        ser = sers.ApplicationCreateSerializer(data=data)
        if ser.is_valid():
            obj = ser.save()
            task_log = TaskLog.objects.create(task_name='send_application_alert', args={'application_id': obj.id})
            send_application_alert.delay(obj.id, task_log.id)
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        ser = sers.ApplicationListSerializer(Application.objects.filter(instructor=request.user.instructor), many=True)
        return Response(ser.data, status=status.HTTP_200_OK)


class ApplicationListView(views.APIView):
    """Get a list of applications made to a lesson request, called by student or parent"""

    def get(self, request, lesson_req_id):
        try:
            lesson_request = LessonRequest.objects.get(id=lesson_req_id)
        except ObjectDoesNotExist:
            return Response({'message': "There is no lesson request with provided id"},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = sers.LessonRequestApplicationsSerializer(lesson_request)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LessonBookingRegisterView(views.APIView):
    """Register a booking for a lesson (o group of lessons) with an instructor"""
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def post(self, request):
        request.data['user_id'] = request.user.id
        serializer = sers.LessonBookingRegisterSerializer(data=request.data)
        if serializer.is_valid():
            stripe_token = serializer.validated_data.pop('stripe_token')
            booking = LessonBooking.objects.filter(user_id=serializer.validated_data['user']['id'],
                                                   quantity=serializer.validated_data['quantity'],
                                                   total_amount=serializer.validated_data['total_amount'],
                                                   application_id=serializer.validated_data['application']['id'],
                                                   status=LessonBooking.REQUESTED).last()
            if not booking:
                booking = LessonBooking.objects.create(user_id=serializer.validated_data['user']['id'],
                                                       quantity=serializer.validated_data['quantity'],
                                                       total_amount=serializer.validated_data['total_amount'],
                                                       application_id=serializer.validated_data['application']['id'])
            # make payment using stripe
            try:
                charge = stripe.Charge.create(amount='{:.0f}'.format(serializer.validated_data['total_amount'] * 100),
                                              currency='usd',
                                              source=stripe_token,
                                              description='Lesson Booking by {} with package {}'.format(
                                                  request.user.email, serializer.data['charge_description'])
                                              )
            except stripe.error.InvalidRequestError as error:
                return Response({'stripeToken': [error.user_message, ]}, status=status.HTTP_400_BAD_REQUEST)
            except stripe.error.StripeError as error:
                return Response({'message': error.user_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as ex:
                return Response({'message': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # register the charge made
            payment = Payment.objects.create(user=request.user, amount=serializer.validated_data['total_amount'],
                                             description='Lesson booking with package {}'.format(
                                                 serializer.validated_data['charge_description']),
                                             charge_id=charge.id)
            with transaction.atomic():
                booking.payment = payment
                booking.description = 'Package {}'.format(serializer.validated_data['charge_description'])
                booking.status = LessonBooking.PAID
                booking.save()
                booking.application.request.status = LESSON_REQUEST_CLOSED
                booking.application.request.save()
                payment.status = PY_PROCESSED
                payment.save()

            task_log = TaskLog.objects.create(task_name='send_booking_invoice', args={'booking_id': booking.id})
            send_booking_invoice.delay(booking.id, task_log.id)
            task_log = TaskLog.objects.create(task_name='', args={})
            send_booking_alert.delay(booking.id, task_log.id)
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDataView(views.APIView):
    """To return data of an application"""

    def get(self, request, app_id):
        try:
            application = Application.objects.get(id=app_id)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not an application with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = sers.ApplicationDataSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GradeLessonView(views.APIView):

    def post(self, request, booking_id):
        booking = LessonBooking.objects.filter(id=booking_id).last()
        if not booking:
            return Response({'message': 'There is no Lesson Booking with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data['booking_id'] = booking.id
        ser_data = sers.DataGradeLessonSerializer(data=data)
        if ser_data.is_valid():
            ser_data.save()
            return Response({'message': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(ser_data.errors, status=status.HTTP_400_BAD_REQUEST)
