from django.conf import settings
from django.urls import reverse_lazy

from core.utils import send_email


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
