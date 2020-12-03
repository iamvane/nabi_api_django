import datetime as dt
import json
import re
import requests
from decimal import Decimal
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.constants import (BENEFIT_AMOUNT, BENEFIT_DISCOUNT, BENEFIT_LESSON, BENEFIT_READY,
                            PACKAGE_ARTIST, PACKAGE_MAESTRO, PACKAGE_TRIAL, PACKAGE_VIRTUOSO)
from core.utils import send_admin_email, send_email
from notices.models import Offer

User = get_user_model()
PACKAGES = {
    PACKAGE_ARTIST: {'lesson_qty': 4, 'discount': 0},
    PACKAGE_MAESTRO: {'lesson_qty': 8, 'discount': 0},
    PACKAGE_VIRTUOSO: {'lesson_qty': 12, 'discount': 5},
    PACKAGE_TRIAL: {'lesson_qty': 1, 'discount': 0},
}
RANGE_HOURS_CONV = {'early-morning': '8to10', 'late-morning': '10to12', 'early-afternoon': '12to3',
                    'late-afternoon': '3to6', 'evening': '6to9'}
TIMEFRAME_TO_STRING = {'early-morning': 'early morning (8am-10am)',
                       'late-morning': 'late morning (10am-12pm)',
                       'early-afternoon': 'early afternoon (12pm-3pm)',
                       'late-afternoon': 'late afternoon (3pm-6pm)',
                       'evening': 'evening (6pm-9pm)'}
ABREV_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
ABREV_DAY_TO_STRING = {'mon': 'Monday', 'tue': 'Tuesday', 'wed': 'Wednesday', 'thu': 'Thursday',
                       'fri': 'Friday', 'sat': 'Saturday', 'sun': 'Sunday'}


def send_alert_request_instructor_ant(instructor, lesson_request, requestor_account):
    # ToDo: delete this
    """Send advice of new request via email for instructors"""
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    template = 'request_advice_email.html'
    plain_template = 'request_advice_email_plain.html'
    subject = 'There is a New Lesson Request Near You'
    location_tuple = requestor_account.get_location(result_type='tuple')
    params = {
        'request_title': lesson_request.title,
        'location': '{}, {}'.format(location_tuple[2], location_tuple[1]),
        'reference_url': '{}/request/{}'.format(settings.HOSTNAME_PROTOCOL, lesson_request.id)
    }
    send_email(from_email, [instructor.user.email], subject, template, plain_template, params)


def send_alert_request_instructor(instructor, lesson_request, requestor_account):
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    location_tuple = requestor_account.get_location(result_type='tuple')
    student_details = ''
    if requestor_account.user.is_parent():
        for tied_student in lesson_request.students.all():
            student_details = ', '.join([student_details, f'{tied_student.name}, {tied_student.age} years old ({lesson_request.skill_level})'])
        if student_details:
            student_details = student_details[2:]
    else:
        student_details = f'{requestor_account.display_name}, {requestor_account.age} years old ({lesson_request.skill_level})'
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['alert_request'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": instructor.user.email},
            "customProperties": [
                {"name": "first_name", "value": instructor.user.first_name},
                {"name": "request_title", "value": lesson_request.title},
                {"name": "instrument", "value": lesson_request.instrument.name},
                {"name": "display_name", "value": requestor_account.display_name},
                {"name": "student_details", "value": student_details},
                {"name": "reference_url", "value": f'{settings.HOSTNAME_PROTOCOL}/request/{lesson_request.id}'},
            ]
            }
    if lesson_request.trial_proposed_datetime:
        if instructor.timezone:
            time_zone = instructor.timezone
        else:
            time_zone = instructor.get_timezone_from_location_zipcode()
        date_str, time_str = get_date_time_from_datetime_timezone(lesson_request.trial_proposed_datetime,
                                                                  time_zone,
                                                                  '%m/%d/%Y',
                                                                  '%I:%M %p')
        data['customProperties'].append({"name": "lesson_date_subject", "value": f'{date_str} at {time_str}'})
        data['customProperties'].append({"name": "lesson_date",
                                         "value": f'{date_str} at {time_str} ({lesson_request.trial_proposed_timezone})'})
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Alert request email could not be send",
                         """An email to alert about a new lesson request could not be send to email {}, lesson request id {}.

                         The status_code for API's response was {} and content: {}""".format(instructor.user.email,
                                                                                             lesson_request.id,
                                                                                             resp.status_code,
                                                                                             resp.content.decode())
                         )
        return None


def send_info_lesson_student_parent(lesson):
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['info_lesson_user'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.booking.user.email},
            "customProperties": [
                {"name": "first_name", "value": lesson.booking.user.first_name},
                {"name": "instructor_name", "value": lesson.instructor.display_name},
                {"name": "instructor_profile", "value": f'{settings.HOSTNAME_PROTOCOL}/profile/{lesson.instructor.id}'},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Alert request email could not be send to user",
                         f"""An email to alert about a new lesson could not be send to email {lesson.booking.user.email}, lesson id {lesson.id}.

                         The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                         )
        return None


def send_info_lesson_instructor(lesson):
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    student_details = lesson.booking.student_details()
    instrument_name = lesson.booking.request.instrument.name
    if lesson.instructor and lesson.instructor.timezone:
        time_zone = lesson.instructor.timezone
    elif lesson.instructor:
        time_zone = lesson.instructor.get_timezone_from_location_zipcode()
    else:
        time_zone = 'US/Eastern'
    date_str, time_str = get_date_time_from_datetime_timezone(lesson.scheduled_datetime,
                                                              time_zone,
                                                              '%m/%d/%Y',
                                                              '%I:%M %p')
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['info_lesson_instructor'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.instructor.user.email},
            "customProperties": [
                {"name": "instructor_name", "value": lesson.instructor.display_name},
                {"name": "lesson_details", "value": f'{student_details.get("name")}, {student_details.get("age")} year old, {instrument_name}'},
                {"name": "schedule_details", "value": f'{date_str} at {time_str} ({time_zone})'},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Alert request email could not be send to instructor",
                         f"""An email to alert about a new lesson could not be send to email {lesson.booking.user.email}, lesson id {lesson.id}.

                         The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                         )
        return None


def send_invoice_booking(booking, payment):
    """Send email with invoice data for a lesson booking"""
    package_name = 'Unknown'
    res = re.match('Package (.+)', booking.description)
    if res and res.groups():
        package_name = res.groups()[0]
    params = {
        'transaction_id': payment.operation_id,
        'package_name': package_name,
        'amount': str(payment.amount),
        'date': payment.payment_date.strftime('%m/%d/%Y')
    }
    headers = {'Authorization': 'Bearer {}'.format(settings.EMAIL_HOST_PASSWORD), 'Content-Type': 'application/json'}
    response = requests.post(settings.SENDGRID_API_BASE_URL + 'mail/send', headers=headers,
                             data=json.dumps({"from": {"email": settings.DEFAULT_FROM_EMAIL, "name": 'Nabi Music'},
                                              "template_id": settings.SENDGRID_EMAIL_TEMPLATES['booking_invoice'],
                                              "personalizations": [{"to": [{"email": booking.user.email}],
                                                                    "dynamic_template_data": params}]
                                              })
                             )
    if response.status_code != 202:
        send_admin_email("[INFO] Error sending email to Parent/Student, with booking invoice",
                         "The error code is {} and response content: {}.".format(response.status_code,
                                                                                 response.content.decode())
                         )


def send_alert_booking(booking, instructor, buyer_account):
    """Send advice of new lesson booking to instructor and administrator"""
    package_name = 'Unknown'
    res = re.match('Package (.+)', booking.description)
    if res and res.groups():
        package_name = res.groups()[0]
    params = {
        'student': buyer_account.display_name,
        'package_name': package_name,
        'lesson_quantity': booking.quantity,
        'date': booking.updated_at.strftime('%m/%d/%Y'),
    }
    headers = {'Authorization': 'Bearer {}'.format(settings.EMAIL_HOST_PASSWORD), 'Content-Type': 'application/json'}
    response = requests.post(settings.SENDGRID_API_BASE_URL + 'mail/send', headers=headers,
                             data=json.dumps({"from": {"email": settings.DEFAULT_FROM_EMAIL, "name": 'Nabi Music'},
                                              "template_id": settings.SENDGRID_EMAIL_TEMPLATES['booking_advice'],
                                              "personalizations": [{"to": [{"email": instructor.user.email}],
                                                                    "dynamic_template_data": params}]
                                              })
                             )
    if response.status_code != 202:
        send_admin_email("[INFO] Error sending email to Parent/Student, with booking invoice",
                         "The error code is {} and response content: {}.".format(response.status_code,
                                                                                 response.content.decode())
                         )
    send_admin_email('New lessons booking',
                     '{buyer_name} booked {package_name} package with {instructor_name} '
                     'Go to the admin dashboard to manage booking.'.format(buyer_name=buyer_account.display_name,
                                                                           package_name=package_name,
                                                                           instructor_name=instructor.display_name)
                     )


def send_info_lesson_graded(lesson):
    """Send email to parent/student about a graded lesson"""
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['info_graded_lesson'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.booking.user.email},
            "customProperties": [
                {"name": "grade", "value": lesson.grade},
                {"name": "grade_comment", "value": lesson.comment},
                {"name": "instructor_name", "value": lesson.instructor.display_name},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Info about graded lesson email could not be send",
                         """An email to info about a graded lesson could not be send to email {}, lesson id {}.

                         The status_code for API's response was {} and content: {}""".format(lesson.instructor.user.email,
                                                                                             lesson.id,
                                                                                             resp.status_code,
                                                                                             resp.content.decode())
                         )
        return None
              

def send_instructor_lesson_completed(lesson):
    """Send email notification to instructor once lesson is graded"""
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['instructor_lesson_completed'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.instructor.user.email},
            "customProperties": [
                {"name": "instructor_name", "value": lesson.instructor.display_name},
    ]
    }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Info about graded lesson email could not be sent",
                         """An email to info about a graded lesson could not be send to email {}, lesson id {}.
                         
                         The status_code for API's response was {} and content: {}""".format(lesson.instructor.user.email,
                                                                                             lesson.id,
                                                                                             resp.status_code,
                                                                                             resp.content.decode())
                         )
        return None


def send_info_request_available(lesson_request, instructor):
    """Send email to instructor about a request available, which match his data"""
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['info_new_request'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": instructor.user.email},
            "customProperties": [
                {"name": "instrument", "value": lesson_request.instrument.name},
                {"name": "first_name", "value": instructor.user.first_name},
                {"name": "request_url", "value": f'{settings.HOSTNAME_PROTOCOL}/new-request/{lesson_request.id}/?userId={instructor.user.id}'},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Info about a new created lesson request could not be send",
                         """An email about a new created lesson request could not be send to email {}, lesson request id {}.

                         The status_code for API's response was {} and content: {}""".format(instructor.user.email,
                                                                                             lesson_request.id,
                                                                                             resp.status_code,
                                                                                             resp.content.decode())
                         )
        return None


def send_trial_confirmation(lesson):
    """Send email to parent/student, when a Trial Lesson is created"""
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    student_details = lesson.booking.student_details()
    instructor_id = lesson.instructor.id if lesson.instructor else 0
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['trial_confirmation'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.booking.user.email},
            "customProperties": [
                {"name": "profile_link", "value": f"{settings.HOSTNAME_PROTOCOL}/profile/{instructor_id}"},
                {"name": "instructor_name", "value": lesson.instructor.display_name if lesson.instructor else ''},
                {"name": "student_name", "value": student_details.get('name')},
                {"name": "first_name", "value": lesson.booking.user.first_name},
                {"name": "instrument", "value": lesson.booking.request.instrument.name},
                {"name": "lesson_availability", "value": lesson.booking.request.availability_as_string()},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Info about a created trial lesson could not be send",
                         """An email about a created trial lesson could not be send to email {}, lesson id {}.

                         The status_code for API's response was {} and content: {}""".format(
                             lesson.booking.user.email,
                             lesson.id,
                             resp.status_code,
                             resp.content.decode())
                         )
        return None


def send_reminder_grade_lesson(lesson_id):
    """Send email to instructor to reminder about a lesson without grade"""
    from lesson.models import Lesson
    lesson = Lesson.objects.get(id=lesson_id)
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['reminder_grade_lesson'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.instructor.user.email},
            "customProperties": [
                {"name": "first_name", "value": lesson.instructor.user.first_name},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Reminder email to grade lesson",
                         f"""An email to reminder an instructor about grade a lesson could not be send to {lesson.instructor.user.email}, lesson id {lesson.id}.

                         The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                         )
        return None


def send_lesson_reminder(lesson_id, user_id):
    """Send email to reminder about a lesson. Parameter user_id points to receiver user"""
    from accounts.models import get_account
    from lesson.models import Lesson
    lesson = Lesson.objects.get(id=lesson_id)
    user = User.objects.get(id=user_id)
    student_details = lesson.booking.student_details()
    account = get_account(user)
    if account.timezone:
        time_zone = account.timezone
    else:
        time_zone = account.get_timezone_from_location_zipcode()
    sch_date, sch_time = get_date_time_from_datetime_timezone(lesson.scheduled_datetime,
                                                              time_zone,
                                                              date_format='%A %-d, %Y',
                                                              time_format='%I:%M %p')
    instrument_name = skill_level = ''
    if lesson.booking.request:
        instrument_name = lesson.booking.request.instrument.name
        skill_level = lesson.booking.request.skill_level
    else:
        if lesson.booking.user.is_parent():
            if lesson.booking.tied_student.tied_student_details and lesson.booking.tied_student.tied_student_details.instrument:
                instrument_name = lesson.booking.tied_student.tied_student_details.instrument.name
                skill_level = lesson.booking.tied_student.tied_student_details.skill_level
        else:
            stu_details = lesson.booking.user.student_details.first()
            if stu_details and stu_details.instrument:
                instrument_name = stu_details.instrument.name
                skill_level = stu_details.skill_level
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['reminder_lesson'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": user.email},
            "customProperties": [
                {"name": "first_name", "value": user.first_name},
                {"name": "student_name", "value": student_details.get('name')},
                {"name": "instrument", "value": instrument_name},
                {"name": "student_details", "value": f"{student_details.get('age')} years old, {skill_level}"},
                {"name": "lesson_date_time", "value": f'{sch_date} at {sch_time} ({time_zone})'},
                {"name": "zoom_link", "value": lesson.booking.instructor.zoom_link},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Reminder lesson email",
                         f"""An email to reminder about a lesson could not be send to {user.email}, lesson id {lesson.id}.

                             The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                         )
        return None


def send_reschedule_lesson(lesson, user, prev_datetime):
    """Send parent/student an email when a lesson is rescheduled"""
    from accounts.models import get_account
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    account = get_account(user)
    if account is None:
        send_admin_email("[INFO] Info about a rescheduled lesson could not be send",
                         f"User {user.id} ({user.email}) in lesson {lesson.id} has not account.")
        return None
    if account.timezone:
        time_zone = account.timezone
    else:
        time_zone = account.get_timezone_from_location_zipcode()
    prev_sch_date, prev_sch_time = get_date_time_from_datetime_timezone(prev_datetime,
                                                                        time_zone,
                                                                        date_format='%A %b %-d, %Y',
                                                                        time_format='%-I:%M %p')
    sch_date, sch_time = get_date_time_from_datetime_timezone(lesson.scheduled_datetime,
                                                              time_zone,
                                                              date_format='%A %b %-d, %Y',
                                                              time_format='%-I:%M %p')
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['reschedule_lesson'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": user.email},
            "customProperties": [
                {"name": "first_name", "value": user.first_name},
                {"name": "previous_date", "value": f'{prev_sch_date} {prev_sch_time} ({time_zone})'},
                {"name": "current_date", "value": f'{sch_date} {sch_time} ({time_zone})'},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Info about a rescheduled lesson could not be send",
                         """An email about a rescheduled lesson could not be send to email {}, lesson id {}.

                         The status_code for API's response was {} and content: {}""".format(
                             user.email,
                             lesson.id,
                             resp.status_code,
                             resp.content.decode())
                         )
        return None


def send_sms_reminder_lesson(lesson_id):
    from accounts.models import get_account
    from lesson.models import Lesson
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return None
    lb = lesson.booking
    stu_details = lb.student_details()
    stu_name = stu_details.get('name')
    if stu_name[-1] == 's' or stu_name[-1] == 'S':
        stu_name = stu_name + "'"
    else:
        stu_name = stu_name + "'s"
    instrument_name = 'music'
    if lb.user.is_parent():
        if lb.tied_student and lb.tied_student.tied_student_details and lb.tied_student.tied_student_details.instrument:
            instrument_name = lb.tied_student.tied_student_details.instrument.name
    else:
        if lb.user.student_details.count():
            details = lb.user.student_details.last()
            if details and details.instrument:
                instrument_name = details.instrument.name
    # send sms to user of lesson
    account = get_account(lb.user)
    if account.timezone:
        time_zone = account.timezone
    else:
        time_zone = account.get_timezone_from_location_zipcode()
    date_str, time_str = get_date_time_from_datetime_timezone(lesson.scheduled_datetime,
                                                              time_zone,
                                                              '%m/%d/%Y',
                                                              '%I:%M %p')
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        client.messages.create(to=lb.user.phonenumber.number, from_=settings.TWILIO_FROM_NUMBER,
                               body=f'\u23f0 Lesson reminder from Nabi Music: {stu_name} {instrument_name} lesson is coming up at {time_str} ({time_zone}). Please get ready and have a great lesson!')
    except Exception as e:
        send_admin_email("[INFO] A reminder lesson sms could not be sent to user",
                         f'A reminder lesson sms could not be sent to number {lesson.booking.user.phonenumber.number} ({lesson.booking.user.email}), lesson id {lesson_id}.'
                         f'Error obtained: {e}'
                         )
    # send sms to instructor of lesson
    if not lesson.instructor:
        return None
    if lesson.instructor.timezone:
        time_zone = lesson.instructor.timezone
    else:
        time_zone = lesson.instructor.get_timezone_from_location_zipcode()
    date_str, time_str = get_date_time_from_datetime_timezone(lesson.scheduled_datetime,
                                                              time_zone,
                                                              '%m/%d/%Y',
                                                              '%I:%M %p')
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        client.messages.create(to=lesson.instructor.user.phonenumber.number, from_=settings.TWILIO_FROM_NUMBER,
                               body=f'\u23f0 Lesson reminder from Nabi Music: {stu_name} {instrument_name} lesson is coming up at {time_str} ({time_zone}). Please get ready and have a great lesson!')
    except Exception as e:
        send_admin_email("[INFO] A reminder lesson sms could not be sent to instructor",
                         f'A reminder lesson sms could not be sent to number {lesson.instructor.user.phonenumber.number} ({lesson.instructor.user.email}), lesson id {lesson_id}.'
                         f'Error obtained: {e}'
                         )


def get_benefit_to_redeem(user):
    """Return a dict for existing benefit that can be used in lesson booking"""
    data = {'free_lesson': False, 'discount': 0, 'amount': 0, 'source': ''}
    benefits = user.benefits.filter(status=BENEFIT_READY)
    active_offer = Offer.get_last_active_offer()

    if active_offer and active_offer.free_lesson:
        data['source'] = 'offer'
        data['free_lesson'] = True
    elif benefits.count() and benefits.filter(benefit_type=BENEFIT_LESSON).exists():
        data['source'] = 'benefit'
        data['free_lesson'] = True
    if data.get('free_lesson'):
        return data

    benefit_discount = benefits.filter(benefit_type=BENEFIT_DISCOUNT)
    if active_offer and active_offer.percent_discount:
        if benefit_discount.exists():
            benefit = benefit_discount.last()
            if benefit.benefit_qty > active_offer.percent_discount:
                data['source'] = 'benefit'
                data['discount'] = benefit.benefit_qty
            else:
                data['source'] = 'offer'
                data['discount'] = Decimal(active_offer.percent_discount)
        else:
            data['source'] = 'offer'
            data['discount'] = Decimal(active_offer.percent_discount)
    elif benefit_discount.exists():
        benefit = benefit_discount.last()
        data['source'] = 'benefit'
        data['discount'] = benefit.benefit_qty

    benefit_amount = benefits.filter(benefit_type=BENEFIT_AMOUNT)
    if benefit_amount.exists():
        benefit = benefit_amount.last()
        data['amount'] = benefit.benefit_qty
    return data


def get_additional_items_booking(user):
    """Return additional items to add in a lesson booking"""
    booking_count = user.lesson_bookings.count()
    if booking_count == 1:
        if user.lesson_bookings.all()[0].quantity == 1:
            data = {'placementFee': Decimal('12.0000')}
        else:
            data = {}
    else:
        data = {}
    benefits = get_benefit_to_redeem(user)
    if benefits.get('discount'):
        data['discounts'] = benefits.get('discount')
    if benefits.get('amount'):
        data['credits'] = benefits.get('amount')
    if benefits.get('free_lesson'):
        data['freeLesson'] = benefits.get('free_lesson')
    return data


def get_booking_data(user, package_name, application):
    """Get data related to booking: total amount, fees, discounts, etc"""
    data = get_additional_items_booking(user)
    data['lessonRate'] = application.rate
    if data.get('freeLesson'):
        data['lessonsPrice'] = application.rate * (PACKAGES[package_name].get('lesson_qty') - 1)
    else:
        data['lessonsPrice'] = application.rate * PACKAGES[package_name].get('lesson_qty')
    # SubTotal is amount to pay if there is not discounts
    sub_total = data['lessonsPrice'] + data.get('placementFee', 0)   # this variable does not include processingFee
    data['processingFee'] = round(Decimal('0.029') * sub_total + Decimal('0.30'), 2)
    data['subTotal'] = round(sub_total + data['processingFee'], 2)   # to display, add processing fee
    # Now, calculate total
    if data.get('discounts'):
        total = round(data['lessonsPrice'] * (Decimal('100.0000') - data.get('discounts')) / Decimal('100.0'), 4)
    else:
        total = data['lessonsPrice']
    total = total - data.get('credits', 0)
    if package_name == 'virtuoso':
        data['virtuosoDiscount'] = PACKAGES[package_name].get('discount')
        total = round(total * (Decimal('100.0000') - data['virtuosoDiscount']) / 100, 4)
    total += data.get('placementFee', 0)
    data['processingFee'] = round(Decimal('0.029') * total + Decimal('0.30'), 2)
    data['total'] = round(total + data['processingFee'], 2)
    return data


def get_booking_data_v2(user, package_name, last_lesson):
    """Get data related to booking: total amount, fees, discounts, etc"""
    data = get_additional_items_booking(user)
    data['lessonRate'] = last_lesson.rate
    if data.get('freeLesson'):
        data['lessonsPrice'] = last_lesson.rate * (PACKAGES[package_name].get('lesson_qty') - 1)
    else:
        data['lessonsPrice'] = last_lesson.rate * PACKAGES[package_name].get('lesson_qty')
    # SubTotal is amount to pay if there is not discounts
    sub_total = data['lessonsPrice'] + data.get('placementFee', 0)   # this variable does not include processingFee
    data['processingFee'] = round(Decimal('0.029') * sub_total + Decimal('0.30'), 2)
    data['subTotal'] = round(sub_total + data['processingFee'], 2)   # to display, add processing fee
    # Now, calculate total
    if data.get('discounts'):
        total = round(data['lessonsPrice'] * (Decimal('100.0000') - data.get('discounts')) / Decimal('100.0'), 4)
    else:
        total = data['lessonsPrice']
    total = total - data.get('credits', 0)
    if package_name == 'virtuoso':
        data['virtuosoDiscount'] = PACKAGES[package_name].get('discount')
        total = round(total * (Decimal('100.0000') - data['virtuosoDiscount']) / 100, 4)
    total += data.get('placementFee', 0)
    data['processingFee'] = round(Decimal('0.029') * total + Decimal('0.30'), 2)
    data['total'] = round(total + data['processingFee'], 2)
    return data


def get_date_time_from_datetime_timezone(datetime_value, time_zone, date_format='%Y-%m-%d', time_format='%H:%M'):
    """Get date and time elements of a datetime, after apply it a time_zone"""
    localize_datetime = datetime_value.astimezone(timezone.pytz.timezone(time_zone))
    return localize_datetime.strftime(date_format), localize_datetime.strftime(time_format)


def get_next_date_same_weekday(previous_date):
    """Return next date with same weekday as previous_date"""
    next_week_day = previous_date.weekday()
    hoy = timezone.now().date()
    today_week_day = hoy.weekday()
    if next_week_day > today_week_day:
        return hoy + dt.timedelta(days=(next_week_day - today_week_day))
    else:
        return hoy + dt.timedelta(days=(next_week_day + (7 - today_week_day)))


def get_availability_field_names_from_availability_json(json_data):
    resp_list = []
    for item in json_data:
        field_name = item.get('day') + RANGE_HOURS_CONV.get(item.get('timeframe'))
        resp_list.append(field_name)
    return resp_list


def send_advice_assigned_instructor(booking):
    """Send email to instructor, about assign him to a lesson/booking"""
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    instrument_name = skill_level = ''
    if booking.request and booking.request.instrument:
        instrument_name = booking.request.instrument.name
    elif booking.application and booking.application.request and booking.application.request.instrument:
        instrument_name = booking.application.request.instrument.name
    if booking.request and booking.request.skill_level:
        skill_level = booking.request.skill_level
    elif booking.application and booking.application.request and booking.application.request.skill_level:
        skill_level = booking.application.request.skill_level
    student_details = booking.student_details()
    lesson = booking.lessons.first()
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['assigned_booking'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": booking.instructor.user.email},
            "customProperties": [
                {"name": "first_name", "value": booking.instructor.user.first_name},
                {"name": "instrument", "value": instrument_name},
                {"name": "skill_level", "value": skill_level},
                {"name": "student_name", "value": student_details.get('name', '') if student_details else ''},
                {"name": "age", "value": student_details.get('age', '') if student_details else ''},
                {"name": "availability", "value": lesson.booking.request.availability_as_string() if lesson else ''},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Advice instructor email for assignment could not be send",
                         """An email to advice instructor about his assignation to booking could not be send to email {}, lesson booking id {}.

                         The status_code for API's response was {} and content: {}""".format(booking.instructor.user.email,
                                                                                             booking.id,
                                                                                             resp.status_code,
                                                                                             resp.content.decode())
                         )
        return None
