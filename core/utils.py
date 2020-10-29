import random
import requests
import string

from datetime import datetime, timedelta
from dateutil import relativedelta
from djchoices import ChoiceItem, DjangoChoices
from hashlib import sha1

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.template import loader

from core.constants import (DAY_MONDAY, DAY_TUESDAY, DAY_WEDNESDAY, DAY_THURSDAY, DAY_FRIDAY, DAY_SATURDAY, DAY_SUNDAY,
                            MONTH_CHOICES)
from core.models import UserToken


class DayChoices(DjangoChoices):
    monday = ChoiceItem(0, DAY_MONDAY)
    tuesday = ChoiceItem(1, DAY_TUESDAY)
    wednesday = ChoiceItem(2, DAY_WEDNESDAY)
    thursday = ChoiceItem(3, DAY_THURSDAY)
    friday = ChoiceItem(4, DAY_FRIDAY)
    saturday = ChoiceItem(5, DAY_SATURDAY)
    sunday = ChoiceItem(6, DAY_SUNDAY)


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


def send_admin_email(subject, content):
    """Send email to admin in text only (not html)"""
    email = EmailMessage(subject=subject, body=content, from_email=settings.DEFAULT_FROM_EMAIL,
                         to=[settings.ADMIN_EMAIL])
    email.send()


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


def generate_random_password(length):
    """Generate a random password with specified length"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))


def generate_token_reset_password(user):
    repeated_token = True
    while repeated_token:
        token = generate_hash(user.email)
        expired_time = timezone.now() + timedelta(days=1)
        try:
            UserToken.objects.create(user=user, token=token, expired_at=expired_time)
        except IntegrityError:
            pass
        else:
            repeated_token = False
    return token


def send_email_template(email, template_name, email_params=None):
    assert (isinstance(email_params, list)) or (email_params is None)
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS[template_name],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": email},
            "customProperties": []
            }
    if email_params:
        data['customProperties'].extend(email_params)
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email(f"[INFO] Error sending email to template {template_name}",
                         f"An email could not be send to email {email}, with params {email_params}.\n"
                         f"Response has status_code {resp.status_code} and content: {resp.content.decode()}"
                         )
        return False
    return True


def build_error_dict(errors):
    """Build dictionary data to return when serializer's result is error.
    errors should be serializer.errors ; key_non_fields is key's name for errors not related to a field"""
    field_errs = {}
    msg_err = ''
    non_field_err = ''
    result = {}
    for k, v in errors.items():
        if k in ['non_field_errors', '__all__']:
            if isinstance(v, list):
                err_list = [str(item) for item in v if not hasattr(item, 'code') or item.code != 'message']
                if err_list:
                    non_field_err = non_field_err + ' '.join(err_list)
                err_msg_list = [str(item) for item in v if hasattr(item, 'code') and item.code == 'message']
                if err_msg_list:
                    msg_err = msg_err + ' '.join(err_msg_list)
            else:
                non_field_err = non_field_err + str(v)
        else:
            if isinstance(v, list):
                err_list = [str(item) for item in v if not hasattr(item, 'code') or item.code != 'message']
                if err_list:
                    field_errs[k] = ' '.join(err_list)
                err_msg_list = [str(item) for item in v if hasattr(item, 'code') and item.code == 'message']
                if err_msg_list:
                    msg_err = msg_err + ' '.join(err_msg_list)
            else:
                field_errs[k] = str(v)

    if msg_err.strip():
        result['message'] = msg_err.strip()
    if field_errs:
        result['fields'] = field_errs
    if non_field_err:
        result['detail'] = non_field_err
    return result
