from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives

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
    email = user.email
    referral_link = '{}/registration?token={}'.format(settings.HOSTNAME_PROTOCOL,
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
    email_message = EmailMultiAlternatives(subject, text_content, from_email, [email])
    email_message.attach_alternative(html_content, 'text/html')
    email_message.send()

