import random
import requests

from django.conf import settings
from django.contrib.gis.measure import D
from django.utils import timezone

from accounts.models import get_account, Instructor, InstructorInstruments
from accounts.utils import add_to_email_list, get_availaibility_field_name_from_dt, remove_contact_from_email_list
from core.constants import PLACE_FOR_LESSONS_ONLINE, SKILL_LEVEL_BEGINNER, SKILL_LEVEL_INTERMEDIATE, SKILL_LEVEL_ADVANCED
from core.models import TaskLog, User
from core.utils import send_admin_email
from nabi_api_django.celery_config import app

from core.models import ScheduledEmail
from .models import Application, Lesson, LessonBooking, LessonRequest
from .utils import (send_alert_application, send_alert_booking, send_alert_request_instructor, send_info_lesson_graded,
                    send_info_lesson_student_parent, send_info_lesson_instructor,
                    send_info_request_available, send_invoice_booking, send_instructor_lesson_graded,
                    send_reschedule_lesson, send_trial_confirmation)


@app.task
def send_request_alert_instructors(request_id, task_log_id):
    """Send an email to instructors in a place near to 50 miles from lesson request location"""
    request = LessonRequest.objects.get(id=request_id)
    account = get_account(request.user)
    if request.place_for_lessons == PLACE_FOR_LESSONS_ONLINE:
        for instructor in Instructor.objects.filter(instruments__name=request.instrument.name):
            send_alert_request_instructor(instructor, request, account)
    else:
        if account and account.coordinates:
            for instructor in Instructor.objects.filter(coordinates__distance_lte=(account.coordinates, D(mi=50)),
                                                        instruments__name=request.instrument.name):
                send_alert_request_instructor(instructor, request, account)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_lesson_info_student_parent(lesson_id, task_log_id):
    """Send an email to student or parent when a lesson is created"""
    lesson = Lesson.objects.get(id=lesson_id)
    send_info_lesson_student_parent(lesson)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_lesson_info_instructor(lesson_id, task_log_id):
    """Send an email to instructor when is assigned to a lesson. Used for trial lesson only."""
    lesson = Lesson.objects.get(id=lesson_id)
    send_info_lesson_instructor(lesson)
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
def send_info_grade_lesson(lesson_id, task_log_id):
    """Send an email to student or parent when a lesson is graded"""
    lesson = Lesson.objects.get(id=lesson_id)
    send_info_lesson_graded(lesson)
    TaskLog.objects.filter(id=task_log_id).delete()

@app.task
def send_instructor_grade_lesson(lesson_id, task_log_id):
    """Send confirmation email to instructor when a lesson is graded"""
    lesson = Lesson.objects.get(id=lesson_id)
    send_instructor_lesson_graded(lesson)
    TaskLog.objects.filter(id=task_log_id).delete()

@app.task
def send_trial_confirm(lesson_id, task_log_id):
    lesson = Lesson.objects.get(id=lesson_id)
    send_trial_confirmation(lesson)
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
    if not resp.content.decode():
        resp_json = {'contact_sample': []}
    else:
        try:
            resp_json = resp.json()
        except Exception as e:
            send_admin_email('ERROR: Data returned by Sendgrid is not json',
                             'Error message: {}\nReturned content: {}'.format(str(e), resp.content.decode())
                             )
            return None
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
    if not resp.content.decode():
        resp_json = {'contact_sample': []}
    else:
        try:
            resp_json = resp.json()
        except Exception as e:
            send_admin_email('ERROR: Data returned by Sendgrid is not json',
                             'Error message: {}\nReturned content: {}'.format(str(e), resp.content.decode())
                             )
            return None
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


@app.task
def send_alert_admin_request_closed(request_id):
    lesson_request = LessonRequest.objects.get(id=request_id)
    send_admin_email('Lesson Request had get 7 applications',
                     f"The Lesson Request with id {request_id} ({lesson_request.title}) "
                     "has 7 applications now and it's closed.""")


@app.task
def send_admin_assign_instructor(request_id):
    lesson_request = LessonRequest.objects.get(id=request_id)
    send_admin_email('A Lesson Request was created',
                     f"Lesson Request with id {request_id} ({lesson_request.title}) was created, "
                     "review and assign it an instructor.""")


@app.task
def send_alert_request_compatible_instructors(request_id, task_log_id):
    l_req = LessonRequest.objects.get(id=request_id)
    if l_req.skill_level == SKILL_LEVEL_BEGINNER:
        req_levels = [SKILL_LEVEL_BEGINNER, SKILL_LEVEL_INTERMEDIATE, SKILL_LEVEL_ADVANCED]
    elif l_req.skill_level == SKILL_LEVEL_INTERMEDIATE:
        req_levels = [SKILL_LEVEL_INTERMEDIATE, SKILL_LEVEL_ADVANCED]
    else:
        req_levels = [SKILL_LEVEL_ADVANCED]
    instructors_instrument = InstructorInstruments.objects.filter(instrument_id=l_req.instrument_id,
                                                                  skill_level__in=req_levels)\
        .values_list('instructor_id', flat=True)
    instructor_ids = []
    lesson = l_req.get_first_lesson()
    if lesson is None:
        send_admin_email('No lesson in booking', f"The lesson request {l_req.id} has not booking with a lesson registered,"
                                                 f"then, check availability of instructor for lesson's date can't be done.")
    else:
        for instructor in Instructor.objects.filter(id__in=instructors_instrument, complete=True):
            if hasattr(instructor, 'availability'):
                field_name = get_availaibility_field_name_from_dt(lesson.scheduled_datetime, instructor.timezone)
                if getattr(instructor.availability, field_name):
                    instructor_ids.append(instructor.id)
        for ins_id in instructor_ids:
            send_info_request_available(l_req, Instructor.objects.get(id=ins_id), lesson.scheduled_datetime)
        send_admin_assign_instructor.apply_async((l_req.id,), countdown=3600)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_scheduled_email():
    """Search for scheduled emails to be send"""
    import lesson.utils
    for sch_email in ScheduledEmail.objects.filter(schedule__lte=timezone.now(), executed=False):
        func = getattr(lesson.utils, sch_email.function_name)
        func(**sch_email.parameters)
        sch_email.executed = True
        sch_email.save()


@app.task
def send_lesson_reschedule(lesson_id, task_log_id, prev_datetime_str):
    lesson = Lesson.objects.get(id=lesson_id)
    prev_datetime = timezone.datetime.strptime(prev_datetime_str, '%Y-%m-%d %H:%M:%S')
    prev_datetime = prev_datetime.astimezone(timezone.utc)
    send_reschedule_lesson(lesson, lesson.booking.user, prev_datetime)
    if lesson.instructor:
        send_reschedule_lesson(lesson, lesson.instructor.user, prev_datetime)
    TaskLog.objects.filter(id=task_log_id).delete()
