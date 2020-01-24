from django.conf import settings
from django.urls import reverse_lazy

from core.utils import send_email


def send_alert_request_instructor(instructor, lesson_request, requestor_account):
    """Send advice of new request via email for instructors"""
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    template = 'request_advice_email.html'
    plain_template = 'request_advice_email_plain.html'
    subject = 'There is a New Request Near You'
    location_tuple = requestor_account.get_location(result_type='tuple')
    params = {
        'request_title': lesson_request.title,
        'location': '{}, {}'.format(location_tuple[2], location_tuple[1]),
        'reference_url': '{}{}'.format(settings.HOSTNAME_PROTOCOL, reverse_lazy('lesson_request_item',
                                                                                kwargs={'pk': lesson_request.id})
                                       )
    }
    send_email(from_email, [instructor.user.email], subject, template, plain_template, params)
