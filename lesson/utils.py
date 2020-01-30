import json
import re
import requests

from django.conf import settings

from core.utils import send_admin_email, send_email


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
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    template = 'booking_advice_email.html'
    plain_template = 'booking_advice_email_plain.html'
    subject = '{} booked lessons with you'.format(buyer_account.display_name)
    package_name = 'Unknown'
    res = re.match('Package (.+)', booking.description)
    if res and res.groups():
        package_name = res.groups()[0]
    params = {
        'buyer_name': buyer_account.display_name,
        'package_name': package_name,
        'lesson_qty': booking.quantity,
    }
    send_email(from_email, [instructor.user.email], subject, template, plain_template, params)
    send_admin_email('New lessons booking',
                     '{buyer_name} booked {package_name} package with {instructor_name} '
                     'Go to the admin dashboard to manage booking.'.format(buyer_name=buyer_account.display_name,
                                                                           package_name=package_name,
                                                                           instructor_name=instructor.display_name)
                     )
