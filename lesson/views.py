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
from django.shortcuts import get_object_or_404

from rest_framework import status, views
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import TiedStudent, get_account
from accounts.utils import get_stripe_customer_id, add_to_email_list_v2
from core.constants import *
from core.models import TaskLog, UserBenefits
from core.permissions import AccessForInstructor, AccessForParentOrStudent
from core.utils import send_admin_email
from payments.models import Payment
from payments.serializers import GetPaymentMethodSerializer

from . import serializers as sers
from .models import Application, LessonBooking, LessonRequest, Lesson
from .tasks import (send_application_alert, send_alert_admin_request_closed, send_booking_alert, send_booking_invoice,
                    send_info_grade_lesson, send_request_alert_instructors, send_lesson_info_student_parent)
from .utils import get_benefit_to_redeem, get_booking_data, get_booking_data_v2, PACKAGES

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
            obj.refresh_from_db()  # to avoid trial_proposed_datetime as string, and get it as datetime
            lesson = None
            if request.user.lesson_bookings.count() == 0:
                lb = LessonBooking.objects.create(user=request.user, quantity=1, total_amount=0, request=obj,
                                                  description='Package trial', status=LessonBooking.TRIAL)
                lesson = Lesson.objects.create(booking=lb,
                                               scheduled_datetime=obj.trial_proposed_datetime,
                                               scheduled_timezone=obj.trial_proposed_timezone,
                                               )
            task_log = TaskLog.objects.create(task_name='send_request_alert_instructors',
                                              args={'request_id': obj.id})
            send_request_alert_instructors.delay(obj.id, task_log.id)
            if lesson:
                task_log = TaskLog.objects.create(task_name='send_lesson_info_student_parent',
                                                  args={'lesson_id': lesson.id})
                send_lesson_info_student_parent.delay(lesson.id, task_log.id)
                add_to_email_list_v2(request.user, ['trial_to_booking'], ['customer_to_request'])
            else:
                add_to_email_list_v2(request.user, [], ['trial_to_booking'])
            ser = sers.LessonRequestDetailSerializer(obj, context={'user': request.user})
            return Response(ser.data, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """Get a list of lesson requests, registered by current user"""
        ser = sers.LessonRequestDetailSerializer(request.user.lesson_requests.exclude(status=LESSON_REQUEST_CLOSED),
                                                 many=True, context={'user': request.user})
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
            obj = ser.save()
            ser = sers.LessonRequestDetailSerializer(obj, context={'user': request.user})
            return Response(ser.data, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete an existing lesson request"""
        try:
            lesson_request = LessonRequest.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonRequestDetailSerializer(lesson_request, context={'user': request.user})
        data = ser.data
        lesson_request.delete()
        return Response(data, status=status.HTTP_200_OK)

    def get(self, request, pk):
        """Get data from existing lesson request"""
        try:
            lesson_request = LessonRequest.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonRequestDetailSerializer(lesson_request, context={'user': request.user})
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
                point = Point(query_ser.validated_data['location'][1], query_ser.validated_data['location'][0], srid=4326)
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
            ser = sers.LessonRequestItemSerializer(result_page, many=True, context={'user': request.user})
        else:
            ser = sers.LessonRequestItemSerializer(result_page, many=True, context={'user': request.user})
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
        if not request.user.instructor.complete:
            return Response({'message': 'Your application was not sent. You must complete your profile'},
                            status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data['instructor_id'] = request.user.instructor.id
        ser = sers.ApplicationCreateSerializer(data=data)
        if ser.is_valid():
            obj = ser.save()
            task_log = TaskLog.objects.create(task_name='send_application_alert', args={'application_id': obj.id})
            send_application_alert.delay(obj.id, task_log.id)
            if Application.objects.filter(request=obj.request).count() == 7:
                obj.request.status = LESSON_REQUEST_CLOSED
                obj.request.save()
                send_alert_admin_request_closed.delay(obj.request.id)
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
    """Register a booking for a lesson (or group of lessons) with an instructor"""
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def post(self, request):
        request.data['userId'] = request.user.id
        serializer = sers.LessonBookingRegisterSerializer(data=request.data)
        if serializer.is_valid():
            package_name = serializer.validated_data['package']
            if request.user.is_parent():
                tied_student = TiedStudent.objects.get(id=request.data.pop('studentId'))
            else:
                tied_student = None
                request.data.pop('studentId')
            last_lesson = Lesson.get_last_lesson(user=request.user, tied_student=tied_student)
            if not last_lesson:
                return Response({'message': 'Looks like you should create a Trial Lesson first'},
                                status=status.HTTP_400_BAD_REQUEST)
            booking_values_data = get_booking_data_v2(request.user, package_name, last_lesson)
            # create/get booking instance
            lesson_qty = PACKAGES[package_name].get('lesson_qty')
            amount = booking_values_data['total']
            booking = LessonBooking.objects.filter(user_id=serializer.validated_data['userId'],
                                                   tied_student=tied_student,
                                                   status=LessonBooking.REQUESTED).first()
            if booking:
                booking.quantity = lesson_qty
                booking.save()
            else:
                booking = LessonBooking.objects.create(user_id=serializer.validated_data['userId'],
                                                       quantity=lesson_qty,
                                                       total_amount=amount,
                                                       instructor=last_lesson.instructor,
                                                       rate=last_lesson.rate,
                                                       status=LessonBooking.REQUESTED)
            # make payment
            pym_status, pym_obj = Payment.make_and_register(request.user, booking.total_amount,
                                                            f'Lesson booking with package {package_name.capitalize()}',
                                                            serializer.validated_data['paymentMethodCode'])
            if pym_status == 'error':
                return Response({'message': pym_obj}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # set status and info for booking and payment instances
            with transaction.atomic():
                for k, v in booking_values_data.items():
                    booking_values_data[k] = str(v)
                booking.details = booking_values_data
                booking.payment = pym_obj
                booking.description = 'Package {}'.format(package_name.capitalize())
                booking.status = LessonBooking.PAID
                booking.save()
                if booking.request:
                    booking.request.status = LESSON_REQUEST_CLOSED
                    booking.request.save()
                if pym_obj:
                    pym_obj.status = PY_APPLIED
                    pym_obj.save()
                if booking.lessons.count() == 0:
                    Lesson.objects.create(booking=booking,
                                          scheduled_datetime=last_lesson.scheduled_datetime,
                                          scheduled_timezone=last_lesson.scheduled_timezone,
                                          instructor=booking.instructor,
                                          rate=booking.rate,
                                          status=Lesson.SCHEDULED)
                add_to_email_list_v2(request.user, [], ['trial_to_booking'])
                # update data for applicable benefits
                UserBenefits.update_applicable_benefits(request.user)

            task_log = TaskLog.objects.create(task_name='send_booking_invoice', args={'booking_id': booking.id})
            send_booking_invoice.delay(booking.id, task_log.id)
            task_log = TaskLog.objects.create(task_name='send_booking_alert', args={'booking_id': booking.id})
            send_booking_alert.delay(booking.id, task_log.id)
            return Response({'message': 'Lesson(s) booked successfully.',
                             'booking_id': booking.id}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationBookingView(views.APIView):
    """To return data for booking an application"""

    def common(self, request, student_id, package='artist'):
        """Execute common operations.
        Return instance of Response or data (dict)"""
        if request.user.is_parent():
            try:
                tied_student = TiedStudent.objects.get(id=student_id)
            except TiedStudent.DoesNotExist:
                return Response({'message': 'There is not student with provided id'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            tied_student = None
        last_lesson = Lesson.get_last_lesson(user=request.user, tied_student=tied_student)
        data = get_booking_data_v2(request.user, package, last_lesson)
        account = get_account(request.user)
        if not account.stripe_customer_id:
            # try to get from Stripe
            try:
                resp_stripe = stripe.Customer.list()
            except Exception:
                resp_stripe = {'data': []}
            cus_id = ''
            for cus in resp_stripe['data']:
                if cus.get('email', '') == account.user.email:
                    cus_id = cus.get('id', '')
                    break
            if cus_id:
                account.stripe_customer_id = cus_id
                account.save()
        if account.stripe_customer_id:
            try:
                stripe_resp = stripe.PaymentMethod.list(customer=account.stripe_customer_id, type='card')
            except Exception as e:
                stripe_resp = {'data': []}
                send_admin_email('Could not get payment methods',
                                 f"Request to Stripe for payment methods of customer {account.stripe_customer_id} ({request.user.email})"
                                 f" generates an error: {str(e)}")
            pm_ser = GetPaymentMethodSerializer(data=stripe_resp['data'], many=True)
            if pm_ser.is_valid():
                data['paymentMethods'] = pm_ser.data
            else:
                send_admin_email('Error parsing method payment data',
                                 f"The following errors were obtained: {pm_ser.errors}"
                                 f" when following data {stripe_resp['data']} was used in GetPaymentMethodSerializer")
                data['paymentMethods'] = []
        else:
            try:
                stripe_customer = stripe.Customer.create(email=request.user.email, name=account.display_name)
            except Exception as e:
                return Response({'message': f'Error creating Customer in Stripe:\n {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            account.stripe_customer_id = stripe_customer.get('id')
            account.save()
            data['paymentMethods'] = []
        try:
            intent = stripe.SetupIntent.create(customer=account.stripe_customer_id)
        except Exception as e:
            return Response({'message': f'Error creating Intent in Stripe:\n {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data['clientSecret'] = intent.client_secret
        return data

    def get(self, request, student_id):
        """Default, with artist package"""
        resp = self.common(request, student_id)
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp, status=status.HTTP_200_OK)

    def post(self, request, student_id):
        """Receiving package name"""
        if not request.data.get('package'):
            return Response({'message': 'Package value is required'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            package = request.data.get('package')
        if not PACKAGES.get(package):
            return Response({'message': 'Package value is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        resp = self.common(request, student_id, package)
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp, status=status.HTTP_200_OK)


class LessonCreateView(views.APIView):
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def post(self, request):
        if not request.data.get('bookingId'):
            lb = None
            create_trial_lesson = False
            if request.user.is_parent():
                tied_student = get_object_or_404(TiedStudent, pk=request.data.get('studentId'))
                if LessonBooking.objects.filter(user=request.user, tied_student=tied_student).count() == 0:
                    create_trial_lesson = True
                    lb = LessonBooking.objects.create(user=request.user, tied_student=tied_student, quantity=1,
                                                      total_amount=0, description='Trial Lesson', status=PACKAGE_TRIAL)
            else:
                if LessonBooking.objects.filter(user=request.user).count() == 0:
                    create_trial_lesson = True
                    lb = LessonBooking.objects.create(user=request.user, quantity=1, total_amount=0,
                                                      description='Trial Lesson', status=PACKAGE_TRIAL)
            if lb:
                request.data['bookingId'] = lb.id
                lb.create_lesson_request()
            elif create_trial_lesson:
                return Response({'message': 'No Booking for Trial Lession could be created'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({'message': 'No BookingId was provided and trial lesson is not allowed'},
                                status=status.HTTP_400_BAD_REQUEST)
        ser = sers.CreateLessonSerializer(data=request.data)
        if ser.is_valid():
            lesson = ser.save()
            lesson.refresh_from_db()  # to avoid scheduled_datetime as string, and get it as datetime
            ser = sers.LessonSerializer(lesson, context={'user': request.user})
            task_log = TaskLog.objects.create(task_name='send_lesson_info_student_parent',
                                              args={'lesson_id': lesson.id})
            send_lesson_info_student_parent.delay(lesson.id, task_log.id)
            return Response(ser.data, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonView(views.APIView):

    def put(self, request, lesson_id):
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'message': 'There is not Lesson with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser_data = sers.UpdateLessonSerializer(data=request.data, instance=lesson, partial=True)
        if ser_data.is_valid():
            lesson = ser_data.save()
            lesson.refresh_from_db()  # to avoid scheduled_datetime as string, and get it as datetime
            ser = sers.LessonSerializer(lesson, context={'user': request.user})
            if request.data.get('grade'):
                task_log = TaskLog.objects.create(task_name='send_info_grade_lesson', args={'lesson_id': lesson.id})
                send_info_grade_lesson.delay(lesson.id, task_log.id)
            return Response(ser.data, status=status.HTTP_200_OK)
        else:
            return Response(ser_data.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, lesson_id):
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'message': 'There is not Lesson with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonSerializer(lesson, context={'user': request.user})
        return Response(ser.data, status=status.HTTP_200_OK)
