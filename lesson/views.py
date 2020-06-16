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
from accounts.utils import get_stripe_customer_id, add_to_email_list_v2
from core.constants import *
from core.models import TaskLog
from core.permissions import AccessForInstructor, AccessForParentOrStudent
from core.utils import send_admin_email
from payments.models import Payment
from payments.serializers import GetPaymentMethodSerializer

from . import serializers as sers
from .models import Application, LessonBooking, LessonRequest, Lesson
from .tasks import send_application_alert, send_booking_alert, send_booking_invoice, send_request_alert_instructors
from .utils import get_benefit_to_redeem, get_booking_data, PACKAGES

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
            if request.user.lesson_bookings.count() == 0:
                lb = LessonBooking.objects.create(user=request.user, quantity=1, total_amount=0, request=obj,
                                                  description='Package trial')
                Lesson.objects.create(booking=lb,
                                      scheduled_datetime=obj.trial_proposed_datetime,
                                      scheduled_timezone=obj.trial_proposed_timezone,
                                      )
            task_log = TaskLog.objects.create(task_name='send_request_alert_instructors',
                                              args={'request_id': obj.id})
            send_request_alert_instructors.delay(obj.id, task_log.id)
            add_to_email_list_v2(request.user, ['request_to_trial'], ['customer_to_request'])
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
            obj = ser.save()
            ser = sers.LessonRequestDetailSerializer(obj)
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
        ser = sers.LessonRequestDetailSerializer(lesson_request)
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
        st_customer_id = get_stripe_customer_id(request.user)
        serializer = sers.LessonBookingRegisterSerializer(data=request.data)
        if serializer.is_valid():
            package_name = serializer.validated_data['package']
            booking_values_data = get_booking_data(request.user, package_name,
                                                   Application.objects.get(id=serializer.validated_data['applicationId'])
                                                   )
            # create/get booking and make the payment
            if booking_values_data.get('freeTrial'):
                lesson_qty = 1
                amount = 0
            else:
                lesson_qty = PACKAGES[package_name].get('lesson_qty')
                amount = booking_values_data['total']
            booking = LessonBooking.objects.filter(user_id=serializer.validated_data['userId'],
                                                   application_id=serializer.validated_data['applicationId'],
                                                   status=LessonBooking.REQUESTED).first()
            if booking:
                booking.quantity = lesson_qty
                booking.save()
            else:
                booking = LessonBooking.objects.create(user_id=serializer.validated_data['userId'],
                                                       quantity=lesson_qty,
                                                       total_amount=amount,
                                                       application_id=serializer.validated_data['applicationId'],
                                                       status=LessonBooking.REQUESTED)
            if booking_values_data.get('freeTrial'):
                # set values to future usage
                payment = None
                new_status_booking = LessonBooking.TRIAL
            else:
                payment = Payment.objects.filter(user=request.user, amount=booking.total_amount,
                                                 status=PY_REGISTERED).first()
                if not payment:
                    # make payment and register it
                    try:
                        st_payment = stripe.PaymentIntent.create(amount=int(round(booking.total_amount * 100, 0)),
                                                                 currency='usd',
                                                                 customer=st_customer_id,
                                                                 payment_method=serializer.validated_data['paymentMethodCode'],
                                                                 off_session=True,
                                                                 confirm=True)
                    except stripe.error.InvalidRequestError as error:
                        return Response({'message': [error.user_message, ]}, status=status.HTTP_400_BAD_REQUEST)
                    except stripe.error.StripeError as error:
                        return Response({'message': error.user_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except Exception as ex:
                        return Response({'message': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    # register the charge made
                    payment = Payment.objects.create(user=request.user, amount=booking.total_amount,
                                                     stripe_payment_method=serializer.validated_data['paymentMethodCode'],
                                                     description='Lesson booking with package {}'.format(package_name.capitalize()),
                                                     operation_id=st_payment.get('id'))
                new_status_booking = LessonBooking.PAID
            with transaction.atomic():
                for k, v in booking_values_data.items():
                    booking_values_data[k] = str(v)
                booking.details = booking_values_data
                booking.payment = payment
                booking.description = 'Package {}'.format(package_name.capitalize())
                booking.status = new_status_booking
                booking.save()
                booking.application.request.status = LESSON_REQUEST_CLOSED
                booking.application.request.save()
                if payment:
                    payment.status = PY_APPLIED
                    payment.save()
                if new_status_booking == LessonBooking.TRIAL:
                    add_to_email_list_v2(request.user, ['trial_to_booking'], ['request_to_trial'])
                else:
                    add_to_email_list_v2(request.user, [], ['trial_to_booking'])

                # get info about benefits, to change status for user_benefits
                benefit_data = get_benefit_to_redeem(request.user)
                user_benefit_ids = []
                if benefit_data.get('free_lesson'):
                    if benefit_data.get('source') == 'benefit':
                        user_benefit = request.user.benefits.filter(status=BENEFIT_READY,
                                                                    benefit_type=BENEFIT_LESSON).first()
                        user_benefit.benefit_qty -= 1
                        if user_benefit.benefit_qty == 0:
                            user_benefit.status = BENEFIT_USED
                            user_benefit_ids.append(user_benefit.id)
                        user_benefit.save()
                else:
                    if benefit_data.get('amount'):   # It's assumed that amount discount is benefit only, not offer
                        user_benefit = request.user.benefits.filter(status=BENEFIT_READY,
                                                                    benefit_type=BENEFIT_AMOUNT).first()
                        user_benefit.status = BENEFIT_USED
                        user_benefit.save()
                        user_benefit_ids.append(user_benefit.id)
                    if benefit_data.get('discount') and benefit_data.get('source') == 'benefit':
                        user_benefit = request.user.benefits.filter(status=BENEFIT_READY,
                                                                    benefit_type=BENEFIT_DISCOUNT).first()
                        user_benefit.status = BENEFIT_USED
                        user_benefit.save()
                        user_benefit_ids.append(user_benefit.id)

                first_book_benefit = request.user.benefits.filter(status=BENEFIT_READY,
                                                                  benefit_type=BENEFIT_DISCOUNT,
                                                                  source='User registration with referral token'
                                                                  ).first()
                if first_book_benefit:
                    first_book_benefit.status = BENEFIT_CANCELLED
                    first_book_benefit.save()
                    user_benefit_ids.append(first_book_benefit.id)
                if user_benefit_ids:
                    request.user.provided_benefits.filter(depends_on__in=user_benefit_ids, status=BENEFIT_PENDING) \
                        .update(status=BENEFIT_READY)

            task_log = TaskLog.objects.create(task_name='send_booking_invoice', args={'booking_id': booking.id})
            send_booking_invoice.delay(booking.id, task_log.id)
            task_log = TaskLog.objects.create(task_name='', args={})
            send_booking_alert.delay(booking.id, task_log.id)
            return Response({'message': 'Lesson(s) booked successfully.',
                             'booking_id': booking.id}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationBookingView(views.APIView):
    """To return data for booking an application"""

    def common(self, request, app_id, package='artist'):
        """Execute common operations.
        Return instance of Response or data (dict)"""
        try:
            application = Application.objects.get(id=app_id)
        except ObjectDoesNotExist:
            return Response({'message': 'There is not an application with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        data = get_booking_data(request.user, package, application)
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

    def get(self, request, app_id):
        """Default, with artist package"""
        resp = self.common(request, app_id)
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp, status=status.HTTP_200_OK)

    def post(self, request, app_id):
        """Receiving package name"""
        if not request.data.get('package'):
            return Response({'message': 'Package value is required'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            package = request.data.get('package')
        if not PACKAGES.get(package):
            return Response({'message': 'Package value is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        resp = self.common(request, app_id, package)
        if isinstance(resp, Response):
            return resp
        else:   # then, its data, not Response
            return Response(resp, status=status.HTTP_200_OK)


class LessonCreateView(views.APIView):

    def post(self, request):
        ser = sers.CreateLessonSerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response({'message': 'Lesson scheduled successfully!'}, status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonUpdateView(views.APIView):

    def put(self, request, lesson_id):
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'message': 'There is not Lesson with provided id'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser_data = sers.UpdateLessonSerializer(data=request.data, instance=lesson, partial=True)
        if ser_data.is_valid():
            ser_data.save()
            return Response({'message': 'Lesson updated successfully!'}, status=status.HTTP_200_OK)
        else:
            return Response(ser_data.errors, status=status.HTTP_400_BAD_REQUEST)
