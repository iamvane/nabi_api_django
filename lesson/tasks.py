import requests

from django.conf import settings
from django.contrib.gis.measure import D
from django.utils import timezone

from accounts.models import get_account, Instructor, InstructorInstruments
from accounts.utils import add_to_email_list, remove_contact_from_email_list
from core.constants import (PLACE_FOR_LESSONS_ONLINE, SKILL_LEVEL_BEGINNER, SKILL_LEVEL_INTERMEDIATE,
                            SKILL_LEVEL_ADVANCED)
from core.models import TaskLog, User
from core.utils import send_admin_email
from nabi_api_django.celery_config import app

from core.models import ScheduledTask
from .models import Lesson, LessonBooking, LessonRequest
from .utils import (get_availability_field_names_from_availability_json, send_advice_assigned_instructor,
                    send_alert_booking, send_info_lesson_graded,
                    send_info_lesson_student_parent, send_info_lesson_instructor,
                    send_invoice_booking, send_reschedule_lesson, send_trial_confirmation,
                    send_instructor_lesson_completed, )
                    

@app.task
def send_lesson_info_student_parent(lesson_id, task_log_id):
    """Send an email to student or parent when a lesson is created"""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        send_admin_email(
            'Error executing send_lesson_info_student_parent task',
            f'Executing task send_lesson_info_student_parent (params: lesson_id {lesson_id}, task_log_id {task_log_id}) '
            f'Lesson DoesNotExist error is raised'
        )
        return None
    send_info_lesson_student_parent(lesson)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_lesson_info_instructor(lesson_id, task_log_id):
    """Send an email to instructor when is assigned to a lesson. Used for trial lesson only."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        send_admin_email(
            'Error executing send_lesson_info_instructor task',
            f'Executing task send_lesson_info_instructor (params: lesson_id {lesson_id}, task_log_id {task_log_id}) '
            f'Lesson DoesNotExist error is raised'
        )
        return None
    send_info_lesson_instructor(lesson)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_booking_invoice(booking_id, task_log_id):
    """Send an email to student or parent (lesson request creator) containing an invoice of booking lesson"""
    try:
        booking = LessonBooking.objects.get(id=booking_id)
    except LessonBooking.DoesNotExist:
        send_admin_email(
            'Error executing send_booking_invoice task',
            f'Executing task send_booking_invoice (params: booking_id {booking_id}, task_log_id {task_log_id}) '
            f'LessonBooking DoesNotExist error is raised'
        )
        return None
    send_invoice_booking(booking, booking.payment)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_booking_alert(booking_id, task_log_id):
    """Send email to instructor which application was booked by a student/parent. And send email to administrator too"""
    try:
        booking = LessonBooking.objects.get(id=booking_id)
    except LessonBooking.DoesNotExist:
        send_admin_email(
            'Error executing send_booking_alert task',
            f'Executing task send_booking_alert (params: booking_id {booking_id}, task_log_id {task_log_id}) '
            f'LessonBooking DoesNotExist error is raised'
        )
        return None
    account = get_account(booking.user)
    if account is None:
        if account is None:
            send_admin_email(
                'Error executing send_booking_alert task',
                f'Executing task send_booking_alert (params: booking_id {booking_id}, task_log_id {task_log_id}) '
                f'no account was obtained for user {booking.user.id} ({booking.user.email})'
            )
            return None
    send_alert_booking(booking, booking.application.instructor, account)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_info_grade_lesson(lesson_id, task_log_id):
    """Send an email to student or parent when a lesson is graded"""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        send_admin_email(
            'Error executing send_info_grade_lesson task',
            f'Executing task send_info_grade_lesson (params: lesson_id {lesson_id}, task_log_id {task_log_id}) '
            f'Lesson DoesNotExist error is raised'
        )
        return None
    send_info_lesson_graded(lesson)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_instructor_complete_lesson(lesson_id, task_log_id):
    """Send confirmation email to instructor when a lesson is graded"""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        send_admin_email(
            'Error executing send_instructor_complete_lesson task',
            f'Executing task send_instructor_complete_lesson (params: lesson_id {lesson_id}, task_log_id {task_log_id}) '
            f'Lesson DoesNotExist error is raised'
        )
        return None
    send_instructor_lesson_completed(lesson)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_trial_confirm(lesson_id, task_log_id):
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        send_admin_email(
            'Error executing send_trial_confirm task',
            f'Executing task send_trial_confirm (params: lesson_id {lesson_id}, task_log_id {task_log_id}) '
            f'Lesson DoesNotExist error is raised'
        )
        return None
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
    try:
        lesson_request = LessonRequest.objects.get(id=request_id)
    except LessonRequest.DoesNotExist:
        send_admin_email(
            'Error executing send_alert_admin_request_closed task',
            f'Executing task send_alert_admin_request_closed (params: request_id {request_id}) '
            f'LessonRequest DoesNotExist error is raised'
        )
        return None
    send_admin_email('Lesson Request had get 7 applications',
                     f"The Lesson Request with id {request_id} ({lesson_request.title}) "
                     "has 7 applications now and it's closed.""")


@app.task
def send_admin_assign_instructor(request_id):
    try:
        lesson_request = LessonRequest.objects.get(id=request_id)
    except LessonRequest.DoesNotExist:
        send_admin_email(
            'Error executing send_admin_assign_instructor task',
            f'Executing task send_admin_assign_instructor (params: request_id {request_id}) '
            f'LessonRequest DoesNotExist error is raised'
        )
        return None
    send_admin_email('A Lesson Request was created',
                     f"Lesson Request with id {request_id} ({lesson_request.title}) was created, "
                     "review and assign it an instructor.""")


@app.task
def send_admin_completed_instructor(lesson_id):
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        send_admin_email(
            'Error executing send_admin_completed_instructor task',
            f'Executing task send_admin_completed_instructor (params: lesson_id {lesson_id}) '
            f'Lesson DoesNotExist error is raised'
        )
        return None
    send_admin_email('An instructor has completed and graded a lesson', 
                     f"Lesson with id {lesson_id} ({lesson.title}) has been completed, "
                     "review and close this lesson.""")
    

@app.task
def execute_scheduled_task():
    """Search for scheduled tasks to be executed"""
    import lesson.utils
    dt_now = timezone.now()
    for sch_task in ScheduledTask.objects.filter(schedule__lte=dt_now, executed=False):
        if sch_task.limit_execution is not None and sch_task.limit_execution < dt_now:
            continue
        try:
            func = getattr(lesson.utils, sch_task.function_name)
            func(**sch_task.parameters)
        except Exception as e:
            send_admin_email('Error executing scheduled tasks',
                             f'Executing function {sch_task.function_name} (register id: {sch_task.id}) the following error was obtained: {e}')
        else:
            sch_task.executed = True
            sch_task.save()


@app.task
def send_lesson_reschedule(lesson_id, task_log_id, prev_datetime_str):
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        send_admin_email(
            'Error executing send_lesson_reschedule task',
            f'Executing task send_lesson_reschedule (params: lesson_id {lesson_id}, task_log_id {task_log_id}, '
            f'prev_datetime_str {prev_datetime_str}) Lesson DoesNotExist error is raised'
        )
        return None
    prev_datetime = timezone.datetime.strptime(prev_datetime_str + '+00:00', '%Y-%m-%d %H:%M:%S%z')
    send_reschedule_lesson(lesson, lesson.booking.user, prev_datetime)
    if lesson.instructor:
        send_reschedule_lesson(lesson, lesson.instructor.user, prev_datetime)
    TaskLog.objects.filter(id=task_log_id).delete()


@app.task
def send_email_assigned_instructor(booking_id, task_log_id):
    try:
        booking = LessonBooking.objects.get(id=booking_id)
    except LessonBooking.DoesNotExist:
        send_admin_email(
            'Error executing send_email_assigned_instructor task',
            f'Executing task send_email_assigned_instructor (params: booking_id {booking_id}) '
            f'LessonBooking DoesNotExist error is raised'
        )
        return None
    send_advice_assigned_instructor(booking)
    TaskLog.objects.filter(id=task_log_id).delete()
