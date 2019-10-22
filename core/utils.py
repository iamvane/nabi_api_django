from datetime import datetime, timedelta
from hashlib import sha1

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.template import loader


def update_model(instance, **kwargs):
    for k, v in kwargs.items():
        if __has_field(instance, k):
            setattr(instance, k, v)
    return instance


def __has_field(instance, name):
    for field in instance._meta.get_fields():
        if field.name == name:
            return True
    return False


def generate_hash(value):
    """Generate an unique hash."""
    now = datetime.utcnow()
    text = '{}{}'.format(value, now.microsecond)
    hash_value = sha1(text.encode())
    return hash_value.hexdigest()


def send_email(sender, receivers, subject, template, template_plain, template_params=None):
    if not isinstance(receivers, list):
        receivers = [receivers, ]
    if template_params is None:
        template_params = {}
    text_content = loader.render_to_string(template_plain, template_params)
    html_content = loader.render_to_string(template, template_params)
    email_message = EmailMultiAlternatives(subject, text_content, sender, receivers)
    email_message.attach_alternative(html_content, 'text/html')
    email_message.send()


def get_date_a_month_later(initial_date):
    final_date = initial_date + timedelta(days=30)
    if final_date.day > initial_date.day:
        while final_date.day != initial_date.day:
            final_date -= timedelta(days=1)
    elif final_date.day < initial_date.day:
        month_ref = final_date.month
        while final_date.day < initial_date.day and final_date.month == month_ref:
            final_date -= timedelta(days=1)
        while final_date.day > initial_date.day:
            final_date -= timedelta(days=1)
    return final_date
