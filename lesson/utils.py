import json
import re
import requests
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from core.constants import (BENEFIT_AMOUNT, BENEFIT_DISCOUNT, BENEFIT_LESSON, BENEFIT_READY,
                            PACKAGE_ARTIST, PACKAGE_MAESTRO, PACKAGE_TRIAL, PACKAGE_VIRTUOSO)
from core.utils import send_admin_email, send_email
from notices.models import Offer

PACKAGES = {
    PACKAGE_ARTIST: {'lesson_qty': 4, 'discount': 0},
    PACKAGE_MAESTRO: {'lesson_qty': 8, 'discount': 0},
    PACKAGE_VIRTUOSO: {'lesson_qty': 12, 'discount': 5},
    PACKAGE_TRIAL: {'lesson_qty': 1, 'discount': 0},
}


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
                {"name": "lesson_location", "value": lesson_request.place_for_lessons},
                {"name": "location", "value": f'{location_tuple[2]} {location_tuple[1]}' if location_tuple else 'N/A'},
                {"name": "reference_url", "value": f'{settings.HOSTNAME_PROTOCOL}/request/{lesson_request.id}'},
            ]
            }
    if lesson_request.trial_proposed_datetime:
        date_str, time_str = get_date_time_from_datetime_timezone(lesson_request.trial_proposed_datetime,
                                                                  lesson_request.trial_proposed_timezone,
                                                                  '%d/%m/%Y',
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
    student_name = ''
    if lesson.student_details:
        student_name = lesson.student_details[0].name
    date_str, time_str = get_date_time_from_datetime_timezone(lesson.scheduled_datetime,
                                                              lesson.scheduled_timezone,
                                                              '%d/%m/%Y',
                                                              '%I:%M %p')
    lesson_request = lesson.booking.get_request()
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['info_lesson'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.booking.user.email},
            "customProperties": [
                {"name": "first_name", "value": lesson.booking.user.first_name},
                {"name": "student_name", "value": student_name},
                {"name": "lesson_date", "value": f'{date_str} at {time_str} ({lesson.scheduled_timezone})'},
                {"name": "instrument", "value": lesson_request.instrument.name},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Alert request email could not be send",
                         f"""An email to alert about a new lesson could not be send to email {lesson.booking.user.email}, lesson id {lesson.id}.

                         The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                         )
        return None


def send_alert_application(application, instructor, request_creator_account):
    """Send advice of new application for a created lesson request"""
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['alert_application'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": request_creator_account.user.email},
            "customProperties": [
                {"name": "request_title", "value": application.request.title},
                {"name": "instructor_name", "value": instructor.display_name},
                {"name": "first_name", "value": instructor.user.first_name},
                {"name": "reference_url",
                 "value": f'{settings.HOSTNAME_PROTOCOL}/application-list/{application.request.id}'},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Alert new application email could not be send",
                         """An email for alert about a new application could not be send to email {}, lesson_request id {}.

                         The status_code for API's response was {} and content: {}""".format(request_creator_account.user.email,
                                                                                             application.request.id,
                                                                                             resp.status_code,
                                                                                             resp.content.decode()
                                                                                             )
                         )
        return False
    return True


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
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": lesson.instructor.user.email},
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
    data['subTotal'] = round(Decimal('1.0290') * sub_total + Decimal('0.30'), 2)   # to display, add processing fee
    if data.get('discounts'):
        total = round(sub_total * (Decimal('100.0000') - data.get('discounts')) / Decimal('100.0'), 4)
    else:
        total = sub_total
    total = total - data.get('credits', 0)
    if package_name == 'virtuoso':
        data['virtuosoDiscount'] = PACKAGES[package_name].get('discount')
        total = round(total * (Decimal('100.0000') - data['virtuosoDiscount']) / 100, 4)
    data['processingFee'] = round(Decimal('0.0290') * total + Decimal('0.30'), 2)
    data['total'] = round(total + data['processingFee'], 2)
    return data


def get_date_time_from_datetime_timezone(datetime_value, time_zone, date_format='%Y-%m-%d', time_format='%H:%M'):
    """Get date and time elements of a datetime, after apply it a time_zone"""
    localize_datetime = datetime_value.astimezone(timezone.pytz.timezone(time_zone))
    return localize_datetime.strftime(date_format), localize_datetime.strftime(time_format)
