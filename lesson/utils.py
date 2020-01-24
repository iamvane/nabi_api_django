from django.conf import settings

from core.utils import send_email


def send_alert_request_instructor(instructor, lesson_request, requestor_account):
    """Send advice of new request via email for instructors"""
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    template = 'request_advice_email.html'
    plain_template = 'request_advice_email_plain.html'
    subject = 'There is a New Request Near You'
    location_tuple = requestor_account.get_location(result_type='tuple')
    params = {'request_title': lesson_request.title, 'location': '{}, {}'.format(location_tuple[2], location_tuple[1])}
    send_email(from_email, [instructor.user.email], subject, template, plain_template, params)
