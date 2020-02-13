import requests

from django.conf import settings
from django.contrib.gis.measure import D
from django.db.models import Q
from django.utils.timezone import now

from accounts.models import get_account, Instructor
from accounts.utils import add_to_email_list, remove_contact_from_email_list
from core.models import TaskLog, User
from core.utils import send_admin_email
from nabi_api_django.celery_config import app

from .models import Application, LessonBooking, LessonRequest
from .utils import send_alert_application, send_alert_booking, send_alert_request_instructor, send_invoice_booking


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
def update_list_users_without_request():
    """Update Sendgrid list of parent/student without lesson request"""
    # first, check parents
    email_set = {email for email in User.objects.filter(parent__isnull=False, lesson_requests__isnull=True)
        .distinct('email').values_list('email', flat=True)}
    header = {'Authorization': 'Bearer {}'.format(settings.EMAIL_HOST_PASSWORD)}
    resp = requests.get('{}marketing/lists/{}?contact_sample=true'.format(
        settings.SENDGRID_API_BASE_URL, settings.SENDGRID_CONTACT_LIST_IDS['parents_without_request']),
        headers=header
    )
    resp_json = resp.json()
    for contact in resp_json.get('contact_sample'):
        email = contact.get('email')
        if email in email_set:
            email_set.remove(email)
        else:
            remove_contact_from_email_list(contact.get('id'), email, 'parents_without_request')
    for email in email_set:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass
        else:
            add_to_email_list(user, 'parents_without_request')
    # now, check students
    email_set = {email for email in User.objects.filter(student__isnull=False, lesson_requests__isnull=True)
        .distinct('email').values_list('email', flat=True)}
    resp = requests.get('{}marketing/lists/{}?contact_sample=true'.format(
        settings.SENDGRID_API_BASE_URL, settings.SENDGRID_CONTACT_LIST_IDS['students_without_request']),
        headers=header
    )
    resp_json = resp.json()
    for contact in resp_json.get('contact_sample'):
        email = contact.get('email')
        if email in email_set:
            email_set.remove(email)
        else:
            remove_contact_from_email_list(contact.get('id'), email, 'students_without_request')
    for email in email_set:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass
        else:
            add_to_email_list(user, 'students_without_request')
