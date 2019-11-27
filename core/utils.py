from datetime import datetime, timedelta
from dateutil import relativedelta
from hashlib import sha1

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.template import loader

from core.constants import MONTH_CHOICES


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


class ElapsedTime:
    years = 0
    months = 0

    def add_time(self, dt_begin, dt_end):
        elapsed = relativedelta.relativedelta(dt_end, dt_begin)
        self.years += elapsed.years
        self.months += elapsed.months

    def re_format(self):
        while self.months > 11:
            self.years += 1
            self.months -= 12


def get_month_integer(month):
    """Return an integer instead of string month"""
    if month == MONTH_CHOICES[0][0]:
        return 1
    elif month == MONTH_CHOICES[1][0]:
        return 2
    elif month == MONTH_CHOICES[2][0]:
        return 3
    elif month == MONTH_CHOICES[3][0]:
        return 4
    elif month == MONTH_CHOICES[4][0]:
        return 5
    elif month == MONTH_CHOICES[5][0]:
        return 6
    elif month == MONTH_CHOICES[6][0]:
        return 7
    elif month == MONTH_CHOICES[7][0]:
        return 8
    elif month == MONTH_CHOICES[8][0]:
        return 9
    elif month == MONTH_CHOICES[9][0]:
        return 10
    elif month == MONTH_CHOICES[10][0]:
        return 11
    elif month == MONTH_CHOICES[11][0]:
        return 12
