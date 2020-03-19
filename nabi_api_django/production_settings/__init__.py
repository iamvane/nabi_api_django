import os
import dj_database_url
from celery.schedules import crontab

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.gis',

    'debug_toolbar',
    'rest_framework',

    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'payments.apps.PaymentsConfig',
    'lesson.apps.LessonConfig',
    'notices',
    'references.apps.ReferencesConfig',
    'background_checks.apps.BackgroundChecksConfig',

    'drf_yasg',
    'corsheaders',
    'storages',
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

ROOT_URLCONF = 'nabi_api_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'nabi_api_django.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME', 'nabidb'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASS', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('PORT', '5432'),
        'OPTIONS': {'sslmode': 'require'},
        'TEST': {
            'NAME': 'nabidb_test',
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

HOSTNAME = "www.nabimusic.com"
HOSTNAME_PROTOCOL = "http://" + HOSTNAME

EMAIL_USE_TLS = True
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'apikey')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', '')
ADMIN_EMAIL = DEFAULT_FROM_EMAIL

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

GOOGLE_FORM_REFERENCES_URL = 'https://forms.gle/MuGhfwUARTW9uzrU9'
SENDGRID_API_BASE_URL = 'https://api.sendgrid.com/v3/'

REST_PAGE_SIZE = 20

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': REST_PAGE_SIZE,
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S'
}

AUTH_USER_MODEL = 'core.User'


import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

sentry_sdk.init(
    dsn="https://e7aee34ab87d4e62ac4570f9c384436c@sentry.io/1774495",
    integrations=[DjangoIntegration()]
)
ignore_logger('django.security.DisallowedHost')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
PROJECT_ROOT   =   os.path.join(os.path.abspath(__file__))
STATIC_ROOT  =   os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra lookup directories for collectstatic to find static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

prod_db  =  dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(prod_db)
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

STATIC_ROOT  =   os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

#  Add configuration for static files storage using whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
]

CORS_ALLOW_CREDENTIALS = True

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    '.herokuapp.com'
]

TWILIO_SERVICE_SID = os.environ['TWILIO_SERVICE_SID']
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


SENDGRID_API_KEY = os.environ['SENDGRID_KEY']
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY

DEFAULT_FROM_EMAIL = os.environ['DEFAULT_FROM_EMAIL']

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

AWS_DEFAULT_ACL = None
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']

AWS_S3_CUSTOM_DOMAIN = '%s.s3.us-east-2.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

AWS_S3_OBJECT_PARAMETERS = {
'CacheControl': 'max-age=86400',
}

GOOGLE_MAPS_API_KEY = os.environ['GOOGLE_MAPS_API_KEY']
STRIPE_PUBLIC_KEY = os.environ['STRIPE_PUBLIC_KEY']
STRIPE_SECRET_KEY = os.environ['STRIPE_SECRET_KEY']

ACCURATE_CLIENT_ID = os.environ['ACCURATE_CLIENT_ID']
ACCURATE_CLIENT_SECRET = os.environ['ACCURATE_CLIENT_SECRET']
ACCURATE_PLAN_PARAMETER = 'PKG_STANDARD'
ACCURATE_PLAN_ADDITIONALS = ['SON', ]

STATIC_LOCATION = 'static'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

MEDIA_LOCATION = 'media'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/'
DEFAULT_FILE_STORAGE = 'core.storage_backends.MediaStorage'

SENDGRID_CONTACT_LIST_IDS = {
    'instructors': os.environ['SENDGRID_CONTACT_LIST_INSTRUCTORS'],
    'parents': os.environ['SENDGRID_CONTACT_LIST_PARENTS'],
    'students': os.environ['SENDGRID_CONTACT_LIST_STUDENTS'],
    'parents_without_request': 'a5bc806b-ce29-4900-ad3b-5e66eaa6e405',
    'students_without_request': 'a7f64112-cf7b-4a26-8f2d-9cb251f3ed00',
}
SENDGRID_EMAIL_TEMPLATES = {
    'booking_invoice': 'd-16bb70c5d4d549ea99d73e2d57cdba84',
    'booking_advice': 'd-b2a6ea08ab8d48cfa180985c966b0061',
}

HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY', 'foo')
HUBSPOT_CONTACT_LIST_IDS = {
    'instructors': '3',
    'parents': '5',
    'students': '10',
    'parents_without_request': 'foo',
    'students_without_request': 'foo',
}

CELERY_BROKER_URL = os.environ['BROKER_URL']
BROKER_POOL_LIMIT = 1
CELERY_BEAT_SCHEDULE = {
    'send-reminder-request': {
        'task': 'lesson.tasks.update_list_users_without_request',
        'schedule': crontab(hour='9'),
    },
}
