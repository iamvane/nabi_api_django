from django.contrib.gis.measure import D
from django.db.models import Q
from django.utils.timezone import now

from accounts.models import get_account, Instructor
from core.models import TaskLog, User
from core.utils import send_admin_email
from nabi_api_django.celery_config import app

from .models import Application, LessonBooking, LessonRequest
from .utils import (send_alert_application, send_alert_booking, send_alert_request_instructor,
                    send_invoice_booking, send_request_reminder)


@app.task
def send_request_alert_instructors(request_id, task_log_id):
    """Send an email to instructors in a place near to 50 miles from lesson request location"""
    request = LessonRequest.objects.get(id=request_id)
    account = get_account(request.user)
    if account and account.coordinates:
        for instructor in Instructor.objects.filter(coordinates__distance_lte=(account.coordinates, D(mi=50))):
            send_alert_request_instructor(instructor, request, account)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_application_alert(application_id, task_log_id):
    """Send an email to student or parent, about a new application placed by an instructor"""
    application = Application.objects.get(id=application_id)
    account = get_account(application.request.user)
    send_alert_application(application, application.instructor, account)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_booking_invoice(booking_id, task_log_id):
    """Send an email to student or parent (lesson request creator) containing an invoice of booking lesson"""
    booking = LessonBooking.objects.get(id=booking_id)
    send_invoice_booking(booking, booking.payment)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_booking_alert(booking_id, task_log_id):
    """Send email to instructor which application was booked by a student/parent. And send email to administrator too"""
    booking = LessonBooking.objects.get(id=booking_id)
    account = get_account(booking.user)
    send_alert_booking(booking, booking.application.instructor, account)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_email_reminder_create_request():
    """Send an email to reminder parent/student to create a lesson request"""
    today = now().date()
    weekday = now().weekday()
    for user in User.objects.filter(Q(parent__isnull=False) | Q(student__isnull=False), lesson_requests__isnull=True)\
            .distinct('email'):
        num_days = today - user.date_joined.date()
        num_days = num_days.days
        if num_days == 28 or (num_days == 29 and user.date_joined.weekday() != 0):
            send_admin_email("[INFO] There is a Parent/Student which has not create a lesson request",
                             "The {rol_name} {display_name} (email {email}) has not create a lesson request "
                             "and there is more than 28 days from his registration.".format(
                                 rol_name=user.get_role(),
                                 display_name=get_account(user).display_name if get_account(user) else '',
                                 email=user.email)
                             )
        elif num_days < 28:
            send_request_reminder(user, num_days, weekday)
