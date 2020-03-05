import json
import re
import requests
from decimal import Decimal

from django.conf import settings

from core.constants import BENEFIT_AMOUNT, BENEFIT_DISCOUNT, BENEFIT_LESSON, BENEFIT_READY
from core.utils import send_admin_email, send_email

PACKAGES = {
    'artist': {'lesson_qty': 4, 'discount': 0},
    'maestro': {'lesson_qty': 8, 'discount': 0},
    'virtuoso': {'lesson_qty': 12, 'discount': 5},
}


def send_alert_request_instructor(instructor, lesson_request, requestor_account):
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


def send_alert_application(application, instructor, request_creator_account):
    """Send advice of new application for a created lesson request"""
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    template = 'application_advice_email.html'
    plain_template = 'application_advice_email_plain.html'
    subject = 'You have a new applicant'
    params = {
        'instructor_name': instructor.display_name,
        'request_title': application.request.title,
        'reference_url': '{}/application-list/{}'.format(settings.HOSTNAME_PROTOCOL, application.request.id)
    }
    send_email(from_email, [request_creator_account.user.email], subject, template, plain_template, params)


def send_invoice_booking(booking, payment):
    """Send email with invoice data for a lesson booking"""
    package_name = 'Unknown'
    res = re.match('Package (.+)', booking.description)
    if res and res.groups():
        package_name = res.groups()[0]
    params = {
        'transaction_id': payment.charge_id,
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


def get_benefit_to_redeem(user):
    """Return a dict for existing benefit that can be used in lesson booking"""
    data = {'free_lesson': False, 'discount': 0, 'amount': 0, 'source': ''}
    benefits = user.benefits.filter(status=BENEFIT_READY)
    response = requests.get('{}/v1/offers-active/'.format(settings.HOSTNAME_PROTOCOL))
    offer_json = response.json()

    if offer_json.get('freeLesson'):
        data['source'] = 'offer'
        data['free_lesson'] = True
    elif benefits.count() and benefits.filter(benefit_type=BENEFIT_LESSON).exists():
        data['source'] = 'benefit'
        data['free_lesson'] = True
    if data.get('free_lesson'):
        return data

    benefit_discount = benefits.filter(benefit_type=BENEFIT_DISCOUNT)
    if offer_json.get('percentDiscount'):
        offer_discount = offer_json.get('percentDiscount')
        if benefit_discount.exists():
            benefit = benefit_discount.last()
            if benefit.benefit_qty > offer_discount:
                data['source'] = 'benefit'
                data['discount'] = benefit.benefit_qty
            else:
                data['source'] = 'offer'
                data['discount'] = Decimal(offer_discount)
        else:
            data['source'] = 'offer'
            data['discount'] = Decimal(offer_discount)
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
    if user.lesson_bookings.count() == 0:
        data = {'freeTrial': True, 'placementFee': Decimal('12.0000')}
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
    data['processingFee'] = Decimal('2.9000')
    sub_total = data['lessonsPrice'] + data.get('placementFee', 0)
    data['subTotal'] = round(sub_total * (Decimal('100.0000') + data.get('processingFee')) / 100, 2)
    if data.get('discounts'):
        total = round(sub_total * (Decimal('100.0000') - data.get('discounts')) / Decimal('100.0'), 4)
    else:
        total = sub_total
    total = total - data.get('credits', 0)
    if package_name == 'virtuoso':
        data['virtuosoDiscount'] = PACKAGES[package_name].get('discount')
        total = round(total * (Decimal('100.0000') - data['virtuosoDiscount']) / 100, 4)
    data['total'] = round(total * (100 + data.get('processingFee')) / 100, 2)
    return data
