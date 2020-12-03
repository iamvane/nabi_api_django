import math
import random
import stripe
from functools import reduce

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.db.models import PointField
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import transaction
from django.db.models import Case, F, ObjectDoesNotExist, Q, When
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, views
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Instructor, InstructorInstruments, TiedStudent, get_account
from accounts.serializers import MinimalTiedStudentSerializer
from accounts.utils import get_stripe_customer_id, add_to_email_list_v2
from core.constants import *
from core.models import ScheduledTask, TaskLog, UserBenefits
from core.permissions import AccessForInstructor, AccessForParentOrStudent
from core.utils import build_error_dict, send_admin_email
from lesson.models import Instrument
from lesson.utils import get_availability_field_names_from_availability_json
from payments.models import Payment
from payments.serializers import GetPaymentMethodSerializer

from . import serializers as sers
from .models import Application, InstructorAcceptanceLessonRequest, LessonBooking, LessonRequest, Lesson
from .tasks import (send_alert_admin_request_closed, send_booking_alert, send_booking_invoice,
                    send_email_assigned_instructor, send_info_grade_lesson,
                    send_lesson_reschedule, send_request_alert_instructors, send_trial_confirm,
                    send_lesson_info_student_parent, send_instructor_complete_lesson,
                    send_instructor_complete_lesson, send_admin_completed_instructor)
from .utils import get_benefit_to_redeem, get_booking_data, get_booking_data_v2, PACKAGES

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


class LessonRequestView(views.APIView):
    """View for usage of parents and students."""
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def post(self, request):
        """Register a lesson request."""
        data = request.data.copy()
        data['user'] = request.user.id
        ser = sers.LessonRequestCreateSerializer(data=data)
        if ser.is_valid():
            obj = ser.save()
            if not LessonBooking.objects.filter(user=request.user, tied_student=obj.students.first()).exists():
                lb = LessonBooking.objects.create(user=obj.user, quantity=1, total_amount=0, request=obj,
                                                  tied_student=obj.students.first(),
                                                  description='Package trial', status=LessonBooking.TRIAL)
                Lesson.objects.create(booking=lb, status=Lesson.PENDING)
                add_to_email_list_v2(request.user, [], ['trial_to_booking'])
            ser = sers.LessonRequestDetailSerializer(obj, context={'user': request.user})
            return Response(ser.data)
        else:
            result = build_error_dict(ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """Get a list of lesson requests, registered by current user"""
        ser = sers.LessonRequestDetailSerializer(request.user.lesson_requests.exclude(status=LESSON_REQUEST_CLOSED),
                                                 many=True, context={'user': request.user})
        return Response(ser.data)


class LessonRequestItemView(views.APIView):
    """View for usage of parents and students."""
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def put(self, request, pk):
        """Update an existing lesson request"""
        try:
            instance = LessonRequest.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response({'detail': 'There is not lesson request with provided id'},
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
            return Response(ser.data)
        else:
            result = build_error_dict(ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete an existing lesson request"""
        try:
            lesson_request = LessonRequest.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({'detail': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonRequestDetailSerializer(lesson_request, context={'user': request.user})
        data = ser.data
        lesson_request.delete()
        return Response(data)

    def get(self, request, pk):
        """Get data from existing lesson request"""
        try:
            lesson_request = LessonRequest.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return Response({'detail': 'There is not lesson request with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonRequestDetailSerializer(lesson_request, context={'user': request.user})
        return Response(ser.data)


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
            result = build_error_dict(query_ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # return data with pagination
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(qs, request)
        if account:
            ser = sers.LessonRequestItemSerializer(result_page, many=True, context={'user': request.user})
        else:
            ser = sers.LessonRequestItemSerializer(result_page, many=True)
        return paginator.get_paginated_response(ser.data)


class LessonRequestItemListView(views.APIView):
    """Return data of a lesson request created by a parent or student"""
    permission_classes = (AllowAny, )

    def get(self, request, pk):
        try:
            lesson_request = LessonRequest.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response({'detail': 'There is not lesson request with provider id'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(request.user, AnonymousUser):
            serializer = sers.LessonRequestListItemSerializer(lesson_request, context={'user': request.user})
        else:
            serializer = sers.LessonRequestListItemSerializer(lesson_request)
        return Response(serializer.data)


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
            ser_data = sers.ApplicationListSerializer(obj, many=False)
            if Application.objects.filter(request=obj.request).count() == 7:
                obj.request.status = LESSON_REQUEST_CLOSED
                obj.request.save()
                send_alert_admin_request_closed.delay(obj.request.id)
            return Response(ser_data.data)
        else:
            result = build_error_dict(ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        ser = sers.ApplicationListSerializer(Application.objects.filter(instructor=request.user.instructor), many=True)
        return Response(ser.data)


class LessonBookingRegisterView(views.APIView):
    """Register a booking for a lesson (or group of lessons) with an instructor"""
    permission_classes = (AllowAny, )

    def post(self, request):
        if isinstance(request.user, AnonymousUser):
            try:
                user = User.objects.get(email=request.data.get('email'))
            except User.DoesNotExist:
                return Response({'detail': 'Does not exist use with provided id'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            user = request.user
        request.data['userId'] = user.id
        serializer = sers.LessonBookingRegisterSerializer(data=request.data)
        if serializer.is_valid():
            package_name = serializer.validated_data['package']
            if user.is_parent():
                if user.parent.tied_students.count() > 1:
                    try:
                        tied_student = TiedStudent.objects.get(id=request.data.pop('studentId'), parent=user.parent)
                    except TiedStudent.DoesNotExist:
                        return Response({'detail': 'There is not student with provided id'},
                                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    tied_student = user.parent.tied_students.first()
            else:
                tied_student = None
                request.data.pop('studentId', '')
            last_lesson = Lesson.get_last_lesson(user=user, tied_student=tied_student)
            if not last_lesson:
                return Response({'detail': 'Looks like you should create a Trial Lesson first'},
                                status=status.HTTP_400_BAD_REQUEST)
            booking_values_data = get_booking_data_v2(user, package_name, last_lesson)
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
                                                       tied_student=tied_student,
                                                       quantity=lesson_qty,
                                                       total_amount=amount,
                                                       instructor=last_lesson.instructor,
                                                       rate=last_lesson.rate,
                                                       status=LessonBooking.REQUESTED)
            # make payment
            pym_status, pym_obj = Payment.make_and_register(user, booking.total_amount,
                                                            f'Lesson booking with package {package_name.capitalize()}',
                                                            serializer.validated_data['paymentMethodCode'])
            if pym_status == 'error':
                return Response({'detail': pym_obj}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
                    booking.create_lessons(last_lesson)
                add_to_email_list_v2(user, [], ['trial_to_booking'])
                # update data for applicable benefits
                UserBenefits.update_applicable_benefits(user)

            task_log = TaskLog.objects.create(task_name='send_booking_invoice', args={'booking_id': booking.id})
            send_booking_invoice.delay(booking.id, task_log.id)
            return Response({'message': 'Lesson(s) booked successfully.', 'booking_id': booking.id})
        else:
            result = build_error_dict(serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class AmountsForBookingView(views.APIView):
    """To return data for booking an application"""

    def common(self, request, student_id, package='artist'):
        """Execute common operations.
        Return instance of Response (for error) or data dict (for successful)"""
        if request.user.is_parent():
            try:
                tied_student = TiedStudent.objects.get(id=student_id)
            except TiedStudent.DoesNotExist:
                return Response({'detail': 'There is not student with provided id'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            tied_student = None
        last_lesson = Lesson.get_last_lesson(user=request.user, tied_student=tied_student)
        if not last_lesson or not last_lesson.rate:
            return Response({'detail': 'Error getting rate from last lesson'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if package not in [PACKAGE_ARTIST, PACKAGE_MAESTRO, PACKAGE_TRIAL, PACKAGE_VIRTUOSO]:
            return Response({'detail': 'Wrong package value'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
                return Response({'detail': f'Error creating Customer in Stripe:\n {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            account.stripe_customer_id = stripe_customer.get('id')
            account.save()
            data['paymentMethods'] = []
        try:
            intent = stripe.SetupIntent.create(customer=account.stripe_customer_id)
        except Exception as e:
            return Response({'detail': f'Error creating Intent in Stripe:\n {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data['clientSecret'] = intent.client_secret
        if last_lesson.instructor:
            data.update({'instructor': {'avatar': last_lesson.instructor.avatar.url,
                                        'reviews': last_lesson.instructor.get_review_dict(),
                                        'backgroundCheckStatus': last_lesson.instructor.bg_status,
                                        'display_name': last_lesson.instructor.display_name,
                                        'rate': last_lesson.rate,
                                        'yearsOfExperience': last_lesson.instructor.years_of_experience,
                                        'age': last_lesson.instructor.age,
                                        }
                         })
        else:
            data.update({'instructor': {'avatar': '',
                                        'reviews': {},
                                        'backgroundCheckStatus': '',
                                        'display_name': '',
                                        'rate': None,
                                        'yearsOfExperience': None,
                                        'age': None,
                                        }
                         })
        return data

    def get(self, request, student_id):
        """Default, with artist package"""
        resp = self.common(request, student_id)
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp)

    def post(self, request, student_id):
        """Receiving package name"""
        if not request.data.get('package'):
            return Response({'detail': 'Package value is required'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            package = request.data.get('package')
        if not PACKAGES.get(package):
            return Response({'detail': 'Package value is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        resp = self.common(request, student_id, package)
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp)


class DataForBookingView(views.APIView):
    """Return data for create a booking. Based in AmountsForBookingView"""
    permission_classes = (AllowAny,)

    def common(self, email, student_id, package):
        """Execute common operations.
        Return instance of Response or data (dict)"""
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'Does not exist user with provided id'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if user.is_parent():
            if user.parent.tied_students.count() > 1:
                try:
                    tied_student = TiedStudent.objects.get(id=student_id, parent=user.parent)
                except TiedStudent.DoesNotExist:
                    ser = MinimalTiedStudentSerializer(user.parent.tied_students.all(), many=True)
                    return Response(ser.data)
            else:
                tied_student = user.parent.tied_students.first()
        else:
            tied_student = None
        last_lesson = Lesson.get_last_lesson(user=user, tied_student=tied_student)
        if not last_lesson or not last_lesson.rate:
            return Response({'detail': 'Error getting rate from last lesson'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if package not in [PACKAGE_ARTIST, PACKAGE_MAESTRO, PACKAGE_TRIAL, PACKAGE_VIRTUOSO]:
            return Response({'detail': 'Wrong package value'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = get_booking_data_v2(user, package, last_lesson)
        account = get_account(user)
        try:
            stripe_customer = stripe.Customer.create(email=user.email, name=account.display_name)
        except Exception as e:
            return Response({'detail': f'Error creating Customer in Stripe:\n {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        account.stripe_customer_id = stripe_customer.get('id')
        account.save()
        data['paymentMethods'] = []
        try:
            intent = stripe.SetupIntent.create(customer=account.stripe_customer_id)
        except Exception as e:
            return Response({'detail': f'Error creating Intent in Stripe:\n {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data['clientSecret'] = intent.client_secret
        if last_lesson.instructor:
            data.update({'instructor': {'avatar': last_lesson.instructor.avatar.url,
                                        'reviews': last_lesson.instructor.get_review_dict(),
                                        'backgroundCheckStatus': last_lesson.instructor.bg_status,
                                        'displayName': last_lesson.instructor.display_name,
                                        'rate': last_lesson.rate,
                                        'yearsOfExperience': last_lesson.instructor.years_of_experience,
                                        'age': last_lesson.instructor.age,
                                        }
                         })
        else:
            data.update({'instructor': {'avatar': '',
                                        'reviews': {},
                                        'backgroundCheckStatus': '',
                                        'displayName': '',
                                        'rate': None,
                                        'yearsOfExperience': None,
                                        'age': None,
                                        }
                         })
        return data

    def get(self, request, email, student_id=None):
        """Default, with artist package"""
        resp = self.common(email, student_id, 'artist')
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp)

    def post(self, request, email, student_id=None):
        """Receiving package name"""
        if not request.data.get('package'):
            return Response({'detail': 'Package value is required'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            package = request.data.get('package')
        if not PACKAGES.get(package):
            return Response({'detail': 'Package value is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        resp = self.common(email, student_id, package)
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp)


class LessonCreateView(views.APIView):
    permission_classes = (IsAuthenticated, AccessForParentOrStudent)

    def post(self, request):
        if not request.data.get('bookingId'):
            lb = None
            create_trial_lesson = False
            if request.user.is_parent():
                try:
                    tied_student = TiedStudent.objects.get(id=request.data.get('studentId'))
                except TiedStudent.DoesNotExist:
                    return Response({'detail': 'There is not student with provided id'}, status=status.HTTP_400_BAD_REQUEST)
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
            elif create_trial_lesson:
                return Response({'detail': 'No Booking for Trial Lesson could be created'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({'detail': 'No BookingId was provided and trial lesson is not allowed'},
                                status=status.HTTP_400_BAD_REQUEST)
        ser = sers.CreateLessonSerializer(data=request.data)
        if ser.is_valid():
            lesson = ser.save()
            ser = sers.LessonSerializer(lesson, context={'user': request.user})
            return Response(ser.data)
        else:
            result = build_error_dict(ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class LessonView(views.APIView):

    def put(self, request, lesson_id):
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'detail': 'There is not Lesson with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        previous_datetime = lesson.scheduled_datetime
        ser_data = sers.UpdateLessonSerializer(data=request.data, instance=lesson, partial=True)
        if ser_data.is_valid():
            lesson = ser_data.save()
            lesson.refresh_from_db()  # to avoid scheduled_datetime as string, and get it as datetime
            ser = sers.LessonSerializer(lesson, context={'user': request.user})
            if request.data.get('grade'):
                task_log = TaskLog.objects.create(task_name='send_info_grade_lesson', args={'lesson_id': lesson.id})
                send_info_grade_lesson.delay(lesson.id, task_log.id)
                task_log = TaskLog.objects.create(task_name='send_instructor_complete_lesson', args={'lesson_id': lesson.id})
                send_instructor_complete_lesson.delay(lesson.id, task_log.id)
                send_admin_completed_instructor.delay(lesson.id)
            elif request.data.get('date'):
                ScheduledTask.objects.filter(function_name='send_reminder_grade_lesson',
                                             parameters__lesson_id=lesson.id,
                                             executed=False)\
                        .update(schedule=lesson.scheduled_datetime + timezone.timedelta(minutes=30),
                                limit_execution=lesson.scheduled_datetime + timezone.timedelta(minutes=60))
                if not ScheduledTask.objects.filter(function_name='send_reminder_grade_lesson',
                                                    parameters__lesson_id=lesson.id,
                                                    executed=False).exists() and lesson.instructor:
                    ScheduledTask.objects.create(function_name='send_reminder_grade_lesson',
                                                 schedule=lesson.scheduled_datetime + timezone.timedelta(minutes=30),
                                                 limit_execution=lesson.scheduled_datetime + timezone.timedelta(
                                                     minutes=60),
                                                 parameters={'lesson_id': lesson.id})
                ScheduledTask.objects.filter(function_name='send_lesson_reminder',
                                             parameters__lesson_id=lesson.id,
                                             executed=False) \
                    .update(schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=60),
                            limit_execution=lesson.scheduled_datetime + timezone.timedelta(minutes=60))
                if not ScheduledTask.objects.filter(function_name='send_lesson_reminder',
                                                    parameters__lesson_id=lesson.id,
                                                    executed=False).exists():
                    ScheduledTask.objects.create(function_name='send_lesson_reminder',
                                                 schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=60),
                                                 limit_execution=lesson.scheduled_datetime + timezone.timedelta(
                                                     minutes=60),
                                                 parameters={'lesson_id': lesson.id, 'user_id': lesson.booking.user.id})
                    if lesson.instructor:
                        ScheduledTask.objects.create(function_name='send_lesson_reminder',
                                                     schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=60),
                                                     limit_execution=lesson.scheduled_datetime + timezone.timedelta(
                                                         minutes=60),
                                                     parameters={'lesson_id': lesson.id,
                                                                 'user_id': lesson.instructor.user.id})

                sch_time = lesson.scheduled_datetime.time()
                minutes_before = 10 if sch_time.minute % 5 == 0 else 15
                ScheduledTask.objects.filter(function_name='send_sms_reminder_lesson',
                                             parameters__lesson_id=lesson.id,
                                             executed=False)\
                    .update(schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=minutes_before),
                            limit_execution=lesson.scheduled_datetime + timezone.timedelta(minutes=10))
                if not ScheduledTask.objects.filter(function_name='send_sms_reminder_lesson',
                                                    parameters__lesson_id=lesson.id,
                                                    executed=False).exists():
                    ScheduledTask.objects.create(
                        function_name='send_sms_reminder_lesson',
                        schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=minutes_before),
                        limit_execution=lesson.scheduled_datetime + timezone.timedelta(minutes=10),
                        parameters={'lesson_id': lesson.id}
                    )

                task_log = TaskLog.objects.create(task_name='send_lesson_reschedule',
                                                  args={'lesson_id': lesson.id,
                                                        'previous_datetime': previous_datetime.strftime('%Y-%m-%d %I:%M %p')})
                send_lesson_reschedule.delay(lesson.id, task_log.id,
                                             previous_datetime.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
            return Response(ser.data)
        else:
            result = build_error_dict(ser_data.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, lesson_id):
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'detail': 'There is not Lesson with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = sers.LessonSerializer(lesson, context={'user': request.user})
        return Response(ser.data)


class AcceptLessonRequestView(views.APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        if isinstance(request.user, AnonymousUser):
            try:
                user = User.objects.get(id=request.data.get('userId'))
            except User.DoesNotExist:
                return Response({'detail': 'There is not User with provided id'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = request.user
        try:
            lr = LessonRequest.objects.get(id=request.data.get('requestId'))
        except LessonRequest.DoesNotExist:
            return Response({'detail': 'There is not LessonRequest with provided id'}, status=status.HTTP_400_BAD_REQUEST)
        decision = request.data.get('accept')
        if decision is None:
            return Response({'detail': 'Value of accept (true/false) is missing'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_instructor():
            return Response({'message': 'You must be an instructor'}, status=status.HTTP_400_BAD_REQUEST)
        if InstructorAcceptanceLessonRequest.objects.filter(instructor=user.instructor, request=lr).exists():
            return Response({'message': 'You already applied to this request.'}, status=status.HTTP_400_BAD_REQUEST)
        InstructorAcceptanceLessonRequest.objects.create(instructor=user.instructor, request=lr, accept=decision)
        return Response({'message': 'Decision registered'})


def get_matching_instructors(request, params):
    if request.skill_level == SKILL_LEVEL_BEGINNER:
        req_levels = [SKILL_LEVEL_BEGINNER, SKILL_LEVEL_INTERMEDIATE, SKILL_LEVEL_ADVANCED]
    elif request.skill_level == SKILL_LEVEL_INTERMEDIATE:
        req_levels = [SKILL_LEVEL_INTERMEDIATE, SKILL_LEVEL_ADVANCED]
    else:
        req_levels = [SKILL_LEVEL_ADVANCED]
    instructors_instrument = InstructorInstruments.objects.filter(instrument_id=request.instrument_id,
                                                                  skill_level__in=req_levels) \
        .values_list('instructor_id', flat=True)
    instructors = Instructor.objects.filter(id__in=instructors_instrument,
                                            languages__icontains=params.data.get('language'),
                                            complete=True,
                                            screened=True,
                                            )
    instructor_list = []
    max_rating = 0.0
    for instructor in instructors:
        if hasattr(instructor, 'availability'):
            field_names = get_availability_field_names_from_availability_json(request.trial_availability_schedule)
            available = False
            for field_name in field_names:
                if getattr(instructor.availability, field_name):
                    available = True
                    break
            if not available:
                continue
            reviews = instructor.get_review_dict()
            rating = float(reviews.get('rating', '0'))
            if rating > max_rating:
                max_rating = rating
            gender_points = 10 if instructor.gender == params.data.get('gender') else 7
            elapsed = timezone.now() - instructor.user.date_joined
            login_points = ((100 - elapsed.days) / 100) * 10
            if login_points < -7:
                login_points = -7
            instructor_list.append({'id': instructor.id, 'rating': rating, 'points': gender_points + login_points})
    if max_rating == 0.0:
        max_rating = 1.0
    return sorted(instructor_list, key=lambda data: data.get('points') + ((data.get('rating') / max_rating) * 10),
                  reverse=True)


def get_best_instructors(instrument_name=None):
    instructor_list = []
    max_rating = 0.0
    if instrument_name:
        ins_qs = Instructor.objects.filter(complete=True, screened=True,
                                           instruments__in=Instrument.objects.filter(name=instrument_name))
    else:
        ins_qs = Instructor.objects.filter(complete=True, screened=True)
    for instructor in ins_qs:
        if hasattr(instructor, 'availability'):
            reviews = instructor.get_review_dict()
            rating = float(reviews.get('rating', '0'))
            if rating > max_rating:
                max_rating = rating
            experience_points = instructor.years_of_experience if instructor.years_of_experience is not None else 0
            elapsed = timezone.now() - instructor.user.date_joined
            login_points = ((100 - elapsed.days) / 100) * 10
            if login_points < -7:
                login_points = -7
            instructor_list.append({'id': instructor.id, 'rating': rating, 'points': experience_points + login_points})
    if max_rating == 0.0:
        max_rating = 1.0
    return sorted(instructor_list, key=lambda data: data.get('points') + ((data.get('rating') / max_rating) * 10),
                  reverse=True)


class BestInstructorsView(views.APIView):
    permission_classes = (AllowAny, )

    def get(self, request):
        if request.query_params.get('instrument'):
            instructors = get_best_instructors(instrument_name=request.query_params.get('instrument'))
            instructor_ids = [item.get('id') for item in instructors[:5]]
            ser = sers.InstructorMatchSerializer(Instructor.objects.filter(id__in=instructor_ids), many=True)
        else:
            instructors = get_best_instructors()
            instructor_ids = [item.get('id') for item in instructors[:4]]
            ser = sers.BestInstructorSerializer(Instructor.objects.filter(id__in=instructor_ids), many=True)
        return Response(ser.data)


class BestInstructorMatchView(views.APIView):

    def get(self, request, request_id):
        try:
            request = LessonRequest.objects.get(id=request_id)
        except LessonRequest.DoesNotExist:
            return Response({'detail': 'There is not LessonRequest with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser_params = sers.GetParamsInstructorMatchSerializer(instance=request)
        instructor_list = get_matching_instructors(request, ser_params)
        if instructor_list:
            max_index = math.ceil(0.25 * len(instructor_list))
            select_inst = random.choice(instructor_list[:max_index])
            instructor = Instructor.objects.get(id=select_inst.get('id'))
            ser = sers.BestInstructorMatchSerializer(instructor)
            data = ser.data
        else:
            data = {}
        return Response(data)


class InstructorsMatchView(views.APIView):

    def get(self, request, request_id, instructor_id):
        try:
            request = LessonRequest.objects.get(id=request_id)
        except LessonRequest.DoesNotExist:
            return Response({'detail': 'There is not LessonRequest with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser_params = sers.GetParamsInstructorMatchSerializer(instance=request)
        instructor_list = get_matching_instructors(request, ser_params)
        max_index = math.ceil(0.5 * len(instructor_list))
        selected_instructor_ids = set()
        population = instructor_list[:max_index]
        qty_cycles = 0
        while len(selected_instructor_ids) < 2 and qty_cycles < 100 and population:
            qty_cycles += 1
            inst = random.choice(population)
            if inst.get('id') == instructor_id:
                continue
            else:
                selected_instructor_ids.add(inst.get('id'))
        population = instructor_list[max_index:]
        qty_cycles = 0
        while len(selected_instructor_ids) < 2 and qty_cycles < 100 and population:
            qty_cycles += 1
            inst = random.choice(population)
            if inst.get('id') == instructor_id:
                continue
            else:
                selected_instructor_ids.add(inst.get('id'))
        ser = sers.InstructorMatchSerializer(Instructor.objects.filter(id__in=selected_instructor_ids), many=True)
        ser2 = sers.InstructorMatchSerializer(Instructor.objects.get(id=instructor_id))
        data = [ser2.data] + ser.data
        return Response(data)


class AssignInstructorView(views.APIView):

    def post(self, request):
        ser = sers.AssignInstructorDataSerializer(data=request.data, context={'user': request.user})
        if ser.is_valid():
            instructor = Instructor.objects.get(id=ser.validated_data.get('instructorId'))
            rate_obj = instructor.instructorlessonrate_set.first()
            rate_value = rate_obj.mins30 if rate_obj else None
            booking = LessonBooking.objects.filter(Q(request_id=ser.validated_data.get('requestId')) |
                                                   Q(application__request_id=ser.validated_data.get('requestId')))\
                .first()
            with transaction.atomic():
                booking.instructor = instructor
                booking.rate = rate_value
                booking.save()
                for lesson in booking.lessons.all():
                    lesson.instructor = instructor
                    lesson.rate = rate_value
                    lesson.save()
            if booking.lessons.count():
                lesson = booking.lessons.first()
                task_log = TaskLog.objects.create(task_name='send_trial_confirm', args={'lesson_id': lesson.id})
                send_trial_confirm.delay(lesson.id, task_log.id)
            task_log = TaskLog.objects.create(task_name='send_email_assigned_instructor',
                                              args={'booking_id': booking.id})
            send_email_assigned_instructor.delay(booking.id, task_log.id)
            return Response({'message': 'Instructor assigned successfully'})
        else:
            result = build_error_dict(ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
