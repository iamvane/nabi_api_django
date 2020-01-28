import requests

from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from core.utils import get_date_a_month_later, send_email, send_admin_email
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
        cta = "Get $5 in Cash"
        text = "Invite your colleagues to join Nabi, and get $5 in cash"
        bullet = "Invite your colleagues to join Nabi, and get $5 in cash."
        todo = "Make sure your profile is 100% complete."
    else:
        cta = "Give 20% off, Get $5"
        text = "Give your friends 20% off music lessons when they book lessons from your referral link. You get $5 in cash!"
        bullet = "Invite your friends to join Nabi, and get $5 in cash."
        todo = "Make sure your student details are set."

    context = {
        'referral_link': referral_link, 'referral_text': text,
        'referral_cta': cta, 'referral_bullet': bullet, 'todo': todo }
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
    user_full_name = '{} {}'.format(first_name, last_name)
    referral_url = '{}/referral/{}'.format(settings.HOSTNAME_PROTOCOL, referral_token)
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
        heading = 'sent you a lesson FREE of fees!'
        description = 'to keep 100% of your earnings.'
    else:
        heading = 'sent you a FREE music lesson!'
        description = 'to get your FREE lesson.'

    params = {'first_name': first_name, 'last_name': last_name, 'date_limit': date_limit,
              'referral_url': referral_url, 'heading': heading, 'description': description}

    if anonymous_message:
        params['anonymous_message']: anonymous_message

    send_email(from_email, [to_email], subject, template, plain_template, params)


def add_to_email_list(user, list_name):
    """Add email of user to Sendgrid's email list, including first_name and last_name if are non-empty"""
    header = {'Authorization': 'Bearer {}'.format(settings.EMAIL_HOST_PASSWORD), 'Content-type': 'application/json'}
    contact = {'email': user.email}
    if user.first_name:
        contact['first_name'] = user.first_name
    if user.last_name:
        contact['last_name'] = user.last_name
    response = requests.put('{}marketing/contacts'.format(settings.SENDGRID_API_BASE_URL),
                            json={'list_ids': [settings.SENDGRID_CONTACT_LIST_IDS.get(list_name)],
                                  'contacts': [contact]},
                            headers=header
                            )
    if response.status_code != 202:
        send_admin_email("[INFO] Contact couldn't be added to {} list".format(list_name),
                         """The contact {} could not be added to {} list in Sendgrid.

                         The status_code for API's response was {} and content: {}""".format(list_name,
                                                                                             contact,
                                                                                             response.status_code,
                                                                                             response.content.decode())
                         )
