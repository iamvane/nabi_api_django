from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from core.utils import get_date_a_month_later, send_email
from core.constants import ROLE_INSTRUCTOR, HOSTNAME_PROTOCOL

def init_kwargs(model, arg_dict):
    return {
        k: v for k, v in arg_dict.items() if k in [
            f.name for f in model._meta.get_fields()
        ]
    }


def send_welcome_email(user_cc):
    user = user_cc.user
    role = user.get_role()
    referral_token = user.referral_token
    to_email = user.email
    referral_link = '{}/registration?token={}'.format(HOSTNAME_PROTOCOL,
        referral_token)

    if role == 'instructor':
        text = "Invite your colleagues to join Nabi and you and them will get a lesson FREE of fees!"
    else:
        text = "Invite people you know to join Nabi and you and them will get a FREE lesson!"

    context = {'referral_link': referral_link, 'referral_text': text }
    text_content = loader.render_to_string('welcome_to_nabi_plain.html', context)
    html_content = loader.render_to_string('welcome_to_nabi.html', context)
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    subject = 'Welcome to Nabi Music!'
    email_message = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email_message.attach_alternative(html_content, 'text/html')
    email_message.send()


def send_referral_invitation_email(user, email):
    role = user.get_role()
    referral_token = user.referral_token
    first_name = user.first_name
    last_name = user.last_name
    date_limit = get_date_a_month_later(timezone.now())
    to_email = email
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    template = 'referral_email.html'
    plain_template = 'referral_email_plain.html'
    user_full_name =  '{} {}'.format(first_name, last_name)
    anonymous_message = ''

    if not user_full_name.strip():
        if role == ROLE_INSTRUCTOR:
            subject = 'Teach a lesson FREE of fees'
            anonymous_message = 'You can teach a music lesson FREE of fees!'
        else:
            subject = 'You got a FREE music lesson'
            anonymous_message = 'You received a FREE music lesson!'
    else:
        subject = user_full_name + ' invited you to Nabi Music'

    if role == ROLE_INSTRUCTOR:
        referral_url = '{}/registration-instructor?token={}'.format(settings.HOSTNAME_PROTOCOL,
            referral_token)
        heading = 'sent you a lesson FREE of fees!'
        description = 'to keep 100% of your earnings.'
    else:
        referral_url =  '{}/registration-student?token={}'.format(settings.HOSTNAME_PROTOCOL,
            referral_token)
        heading = 'sent you a FREE music lesson!'
        description = 'to get your FREE lesson.'

    params = {'first_name': first_name, 'last_name': last_name, 'date_limit': date_limit,
        'referral_url': referral_url, 'heading': heading, 'description': description}

    if anonymous_message:
        params['anonymous_message']: anonymous_message

    send_email(from_email, [to_email], subject, template, plain_template, params)
