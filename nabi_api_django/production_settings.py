import dj_database_url
import os
import sentry_sdk
from celery.schedules import crontab
from datetime import timedelta
from sentry_sdk.integrations.django import DjangoIntegration
from django.core.exceptions import DisallowedHost

ALLOWED_HOSTS = [
    'localhost',
    '.herokuapp.com'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

DATABASES = {
    'default': dj_database_url.config(conn_max_age=500)
}
DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHITELIST = [
    'https://nabimusic.herokuapp.com',
    'https://www.nabimusic.com',
    'http://www.nabimusic.com',
    'http://www.nabimusiccenter.com',
    'https://www.nabimusiccenter.com',
    'https://nabimusicstaging.herokuapp.com',
    'https://nabinextprod.herokuapp.com',
    'https://nabinext.herokuapp.com',
    'http://nabimusic.com',
    'https://nabimusic.com',
    'http://localhost:3000'
]

EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'test@nabimusic.com'
ADMIN_EMAIL = 'info@nabimusic.com'

AWS_DEFAULT_ACL = None
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_REGION_NAME = os.environ['AWS_REGION_NAME']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_REGION_NAME}.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_S3_USAGE = True

STATIC_LOCATION = 'static'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

MEDIA_LOCATION = 'media'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/'
DEFAULT_FILE_STORAGE = 'core.storage_backends.MediaStorage'


def omit_invalid_hostname(event, hint):
    """Don't log django.DisallowedHost errors in Sentry"""
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, DisallowedHost):
            return None
    return event

sentry_sdk.init(
    dsn=os.environ['SENTRY_DSN'],
    integrations=[DjangoIntegration()],
    before_send=omit_invalid_hostname,
)


# # # Celery configuration # # #
CELERY_BEAT_SCHEDULE = {
    # Note: here, hours are taken in UTC
    # 'send-reminder-request': {
    #     'task': 'lesson.tasks.update_list_users_without_request',
    #     'schedule': crontab(hour='9'),
    # },
    # 'alert-user-without-coordinates-location': {
    #     'task': 'accounts.tasks.alert_user_without_location_coordinates',
    #     'schedule': crontab(hour='7', minute='0'),
    # },
    'execute-scheduled-tasks': {
        'task': 'lesson.tasks.execute_scheduled_task',
        'schedule': crontab(minute='*/5'),
    },
}


# # # Third-party services # # #
GOOGLE_FORM_REFERENCES_URL = 'https://forms.gle/MuGhfwUARTW9uzrU9'

SENDGRID_CONTACT_LIST_IDS = {
    'parents_without_request': 'a5bc806b-ce29-4900-ad3b-5e66eaa6e405',
    'students_without_request': 'a7f64112-cf7b-4a26-8f2d-9cb251f3ed00',
}
SENDGRID_EMAIL_TEMPLATES = {
    'booking_invoice': 'd-16bb70c5d4d549ea99d73e2d57cdba84',
    'booking_advice': 'd-b2a6ea08ab8d48cfa180985c966b0061',
}

SENDGRID_EMAIL_TEMPLATES_USER = {
    'password_reset': 'd-0ed0cdc8b8a4459099acc1873c576940',
    'referral_email': 'd-ec262894f3d74ae289b90e061a9f7200',
    'lesson_reminder': 'd-fa4f06ff0fd149259bca8462a0bba33d',
}

SENDGRID_EMAIL_TEMPLATES_PARENT_STUDENT = {
    'meet_instructor': 'd-3f980e9d5e6044e88c40619091708635',
    'lesson_graded': 'd-2f55697a64834929a5ba6a833b1f2d42',
}

SENDGRID_EMAIL_TEMPLATES_INSTRUCTOR = {
    'new_trial_scheduled': 'd-f5545406b8774196b7ce8b3ca4bdc236',
    'reminder_grade_lesson': 'd-b29bdf1d567b4cddb48563a57122fb9c',
}

HUBSPOT_CONTACT_LIST_IDS = {
    'instructors': '3',
    'parents': '5',
    'students': '10',
    'facebook_lead': '55',
    'incomplete_profiles': '131',
    'customer_to_request': '132',
    'request_to_trial': '133',
    'trial_to_booking': '161',
    'parents_without_request': 'foo',
    'students_without_request': 'foo',
}
HUBSPOT_TEMPLATE_IDS = {
    'alert_application': '27908927674',
    'alert_request': '27862630310',
    'info_request': '30861071713',
    'info_new_request': '33651799070',
    'reminder_lesson': '33862178879',
    'reschedule_lesson': '33901672785',
    'reset_password': '29982554190',   # when user is crated via admin
    'trial_confirmation': '33858534253',
    'instructor_lesson_completed': '33722126483',   # when instructor has graded a lesson
    'assigned_booking': '36987478562',
    'instructor_info_review': '34303391620',
}
